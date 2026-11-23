import logging
import os
from contextlib import contextmanager
from typing import Iterator

from psycopg2 import InterfaceError, OperationalError, pool
from psycopg2.extensions import connection, cursor
from psycopg2.extras import RealDictCursor

log = logging.getLogger(__name__)

db_pool: pool.ThreadedConnectionPool | None = None


class DatabaseUnavailable(Exception):
    """Could not get a connection to PostgreSQL (becomes HTTP 503)."""


def create_pool() -> pool.ThreadedConnectionPool | None:
    # The pool is only created on the first request (and recreated if it fails),
    # so the backend is not left without a database forever if it starts before
    # Postgres. Variables are read here (not at import time) so the tests can
    # point to the test database.
    global db_pool
    if db_pool is None:
        try:
            db_pool = pool.ThreadedConnectionPool(
                1,
                int(os.getenv("DB_POOL_MAX", "10")),
                host=os.getenv("DB_HOST", "localhost"),
                dbname=os.getenv("DB_NAME", "database"),
                user=os.getenv("DB_USER", "admin"),
                password=os.getenv("DB_PASSWORD", "changeme"),
                port=os.getenv("DB_PORT", "5432"),
                connect_timeout=5,
            )
        except OperationalError as e:
            log.error("Error connecting to the database: %s", e)
    return db_pool


def get_db_connection() -> connection | None:
    if create_pool():
        return db_pool.getconn()
    return None


def release_db_connection(conn: connection | None, discard: bool = False) -> None:
    if db_pool and conn:
        db_pool.putconn(conn, close=discard)


def close_pool() -> None:
    global db_pool
    if db_pool is not None:
        db_pool.closeall()
        db_pool = None


@contextmanager
def transaction() -> Iterator[cursor]:
    """Opens a cursor (rows as dicts) inside a transaction.

    - commit if the block ends normally (including with `return`);
    - rollback if an exception is raised;
    - the connection ALWAYS goes back to the pool (the old code leaked
      connections on early `return`s and never committed).
    """
    conn = get_db_connection()
    if conn is None:
        raise DatabaseUnavailable()

    discard = False
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            yield cur
        conn.commit()
    except Exception as e:
        # A broken connection (e.g. Postgres restarted) must not go back to the pool
        if isinstance(e, (OperationalError, InterfaceError)):
            discard = True
        try:
            conn.rollback()
        except Exception:
            discard = True
        raise
    finally:
        release_db_connection(conn, discard=discard)
