"""Authentication - Sprint 1 routes, fixed in Sprint 2 (see docs/pdca-sprint2.md)."""
from flask import jsonify
from flask_jwt_extended import create_access_token, get_jwt, get_jwt_identity, verify_jwt_in_request
from psycopg2 import errors
from werkzeug.security import check_password_hash, generate_password_hash

import database as db
from validations import normalize_text, validate_email, validate_name, validate_password, validate_user

from .api import api, error_response, request_data


@api.get("/health")
def health():
    return jsonify(status="ok")


@api.post("/register")
def register():
    d = request_data()
    username = (d.get("username") or "").strip()
    email = (d.get("email") or "").strip().lower()
    password = d.get("password") or ""
    name = normalize_text(d.get("name"))
    program = normalize_text(d.get("program"))[:100] or None

    if not all([username, email, password, name]):
        return error_response("required fields: username, email, name, password", 400)

    # Validate BEFORE opening a database connection
    if not validate_user(username):
        return error_response("invalid username (3-20 characters: letters, digits or _)", 400)
    if not validate_email(email):
        return error_response("invalid email", 400)
    if not validate_name(name):
        return error_response("invalid name (enter first and last name, no special characters)", 400)
    if not validate_password(password):
        return error_response("weak password (min. 8 characters, with uppercase, lowercase, digit and one of @$!%*?&#)", 400)

    try:
        with db.transaction() as cur:
            cur.execute(
                "SELECT LOWER(username) = LOWER(%s) AS user_dup, LOWER(email) = LOWER(%s) AS email_dup "
                "FROM users WHERE LOWER(username) = LOWER(%s) OR LOWER(email) = LOWER(%s)",
                (username, email, username, email),
            )
            rows = cur.fetchall()
            user_dup = any(r["user_dup"] for r in rows)
            email_dup = any(r["email_dup"] for r in rows)
            if user_dup and email_dup:
                return error_response("username and email already registered", 409)
            if user_dup:
                return error_response("username already registered", 409)
            if email_dup:
                return error_response("email already registered", 409)

            cur.execute(
                "INSERT INTO users (username, name, email, password_hash, program) "
                "VALUES (%s, %s, %s, %s, %s) RETURNING id",
                # salted hash (werkzeug scrypt/pbkdf2) instead of plain sha256
                (username, name, email, generate_password_hash(password), program),
            )
            new_id = cur.fetchone()["id"]
    except errors.UniqueViolation:  # simultaneous registration with the same data
        return error_response("username or email already registered", 409)

    return jsonify(status="success", user={"id": new_id, "username": username, "email": email, "name": name}), 201


@api.post("/login")
def login():
    # Already authenticated: return the token owner (no username/password needed)
    if verify_jwt_in_request(optional=True):
        return jsonify(status="success", logged_as=get_jwt().get("username", get_jwt_identity())), 200

    d = request_data()
    user = (d.get("user") or d.get("username") or d.get("email") or "").strip()
    password = d.get("password") or ""
    if not user or not password:
        return error_response("username and/or password not sent", 400)

    with db.transaction() as cur:
        cur.execute(
            "SELECT id, username, password_hash FROM users WHERE LOWER(email) = LOWER(%s) OR LOWER(username) = LOWER(%s)",
            (user, user),
        )
        row = cur.fetchone()

    # Same message for "does not exist" and "wrong password" (does not reveal which users exist)
    if not row or not check_password_hash(row["password_hash"], password):
        return error_response("invalid username or password", 401)

    token = create_access_token(identity=str(row["id"]), additional_claims={"username": row["username"]})
    return jsonify(status="success", access_token=token, logged_as=row["username"]), 200
