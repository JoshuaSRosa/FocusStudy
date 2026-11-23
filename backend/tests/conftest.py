"""Test infrastructure.

- Pure unit tests (test_unit_*) do not use the database and run anywhere.
- Endpoint tests use a REAL PostgreSQL in a separate database (TEST_DB_NAME,
  default `focusstudy_test`), recreated from database/init.sql on every
  run and emptied before each test. If Postgres is not reachable, these
  tests are SKIPPED with the reason (use `pytest -rs`).
"""
import os
import sys
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))
sys.path.insert(0, str(Path(__file__).resolve().parent))

# The test database ALWAYS overrides DB_NAME (even inside the backend
# container, where DB_NAME points to the real database).
os.environ["DB_NAME"] = os.environ.get("TEST_DB_NAME", "focusstudy_test")
os.environ.setdefault("JWT_SECRET_KEY", "test-key-with-more-than-32-bytes-for-hs256")

INIT_SQL = Path(os.environ.get("INIT_SQL_PATH", BACKEND.parent / "database" / "init.sql"))
TABLES = "pauses, sessions, pdfs, courses, users"

import psycopg2  # noqa: E402

import clock  # noqa: E402
import database  # noqa: E402
from main import create_app  # noqa: E402
from requirements_catalog import REQUIREMENTS  # noqa: E402


# ---------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------
def _connect(dbname: str):
    return psycopg2.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=os.getenv("DB_PORT", "5432"),
        user=os.getenv("DB_USER", "admin"),
        password=os.getenv("DB_PASSWORD", "changeme"),
        dbname=dbname,
        connect_timeout=3,
    )


@pytest.fixture(scope="session")
def db():
    name = os.environ["DB_NAME"]
    if not name.endswith("_test"):
        pytest.exit(f"Refused: the test database must end with '_test' (got '{name}')", returncode=2)
    try:
        admin = _connect("postgres")
    except psycopg2.OperationalError as e:
        pytest.skip(f"PostgreSQL unavailable for endpoint tests: {str(e).strip()}")
    admin.autocommit = True
    with admin.cursor() as cur:
        cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", (name,))
        if not cur.fetchone():
            cur.execute(f'CREATE DATABASE "{name}"')
    admin.close()

    conn = _connect(name)
    conn.autocommit = True
    with conn.cursor() as cur:
        cur.execute("DROP SCHEMA IF EXISTS public CASCADE; CREATE SCHEMA public;")
        cur.execute(INIT_SQL.read_text(encoding="utf-8"))  # init.sql itself is verified here
    yield conn
    database.close_pool()
    conn.close()


@pytest.fixture
def app(db, tmp_path):
    with db.cursor() as cur:
        cur.execute(f"TRUNCATE {TABLES} RESTART IDENTITY CASCADE")
    return create_app({"TESTING": True, "UPLOAD_DIR": str(tmp_path / "uploads")})


@pytest.fixture
def client(app):
    return app.test_client()


# ---------------------------------------------------------------------
# Authenticated users
# ---------------------------------------------------------------------
PASSWORD = "Secret@123"


def register_and_login(client, username: str) -> dict:
    r = client.post(
        "/api/register",
        data={"username": username, "email": f"{username}@focus.com", "name": "Test Student", "password": PASSWORD},
    )
    assert r.status_code == 201, r.get_json()
    r = client.post("/api/login", data={"user": username, "password": PASSWORD})
    assert r.status_code == 200, r.get_json()
    return {"Authorization": f"Bearer {r.get_json()['access_token']}"}


@pytest.fixture
def auth(client):
    return register_and_login(client, "student_a")


@pytest.fixture
def auth_b(client):
    return register_and_login(client, "student_b")


@pytest.fixture
def create_course(client):
    def _create(headers, name="Cálculo I", teacher="Prof. Ana"):
        r = client.post("/api/courses", json={"name": name, "teacher": teacher}, headers=headers)
        assert r.status_code == 201, r.get_json()
        return r.get_json()["course"]

    return _create


# ---------------------------------------------------------------------
# Controllable clock (BR-03 / BR-04)
# ---------------------------------------------------------------------
class FakeClock:
    def __init__(self):
        self.current = datetime(2026, 11, 23, 14, 0, 0, tzinfo=timezone.utc)

    def now(self) -> datetime:
        return self.current

    def advance(self, minutes: float = 0, seconds: float = 0) -> None:
        self.current += timedelta(minutes=minutes, seconds=seconds)


@pytest.fixture
def fake_clock(monkeypatch):
    c = FakeClock()
    monkeypatch.setattr(clock, "now", c.now)
    return c


# ---------------------------------------------------------------------
# Traceability plugin (GRE2)
# ---------------------------------------------------------------------
_reqs_by_test: dict[str, tuple[str, ...]] = {}
_result: dict[str, str] = {}


def pytest_addoption(parser):
    parser.addoption(
        "--traceability",
        action="store_true",
        help="prints the requirement -> tests -> result matrix at the end",
    )


def pytest_collection_modifyitems(config, items):
    for item in items:
        ids = tuple(i for m in item.iter_markers("req") for i in m.args)
        unknown = [i for i in ids if i not in REQUIREMENTS]
        if unknown:
            raise pytest.UsageError(f"{item.nodeid}: unknown requirement(s) {unknown}")
        _reqs_by_test[item.nodeid] = ids


def pytest_runtest_logreport(report):
    if report.when == "call" or report.outcome != "passed":
        # a failure/skip during setup also counts
        if report.nodeid not in _result or report.outcome != "passed":
            _result[report.nodeid] = report.outcome


def pytest_terminal_summary(terminalreporter, exitstatus, config):
    if not config.getoption("--traceability"):
        return
    by_req: dict[str, list[str]] = defaultdict(list)
    for nodeid, ids in _reqs_by_test.items():
        for i in ids:
            by_req[i].append(nodeid)

    tr = terminalreporter
    tr.section("Traceability matrix (requirement -> tests)")
    tr.write_line(f"{'ID':<7} {'Tests':>6} {'Pass':>5} {'Fail':>5} {'Skip':>5}  Status      Description")
    for rid, description in REQUIREMENTS.items():
        tests = by_req.get(rid, [])
        passed = sum(_result.get(t) == "passed" for t in tests)
        failed = sum(_result.get(t) == "failed" for t in tests)
        skipped = sum(_result.get(t) == "skipped" for t in tests)
        if not tests:
            status = "NO TEST"
        elif failed:
            status = "FAILED"
        elif skipped:
            status = "INCOMPLETE"
        else:
            status = "VERIFIED"
        tr.write_line(f"{rid:<7} {len(tests):>6} {passed:>5} {failed:>5} {skipped:>5}  {status:<11} {description}")
