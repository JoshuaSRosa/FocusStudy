"""/api blueprint and shared helpers.

Routes are split by subject:
  - auth.py     -> /health, /register, /login       (Sprint 1, fixed)
  - courses.py  -> /courses, /courses/<id>/pdf      (FR-01..FR-05)
  - sessions.py -> /sessions                        (FR-06, FR-07)
"""
from datetime import datetime, timezone

from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt_identity

api = Blueprint("api", __name__, url_prefix="/api")


def error_response(message: str, http_status: int, **extra):
    """Single API error format: {"status": "error", "error": "..."}"""
    return jsonify(status="error", error=message, **extra), http_status


def request_data() -> dict:
    """Accepts JSON or form data (the Sprint 1 frontend uses forms)."""
    if request.is_json:
        data = request.get_json(silent=True)
        return data if isinstance(data, dict) else {}
    return request.form.to_dict()


def current_user_id() -> int:
    """ID of the token owner (the JWT identity is the id as text)."""
    return int(get_jwt_identity())


def to_positive_int(value) -> int | None:
    """Converts ids sent by the client; None if invalid."""
    if isinstance(value, bool):
        return None
    try:
        n = int(str(value).strip())
    except (TypeError, ValueError):
        return None
    return n if n > 0 else None


def iso(dt: datetime | None) -> str | None:
    """Timestamps always in UTC, ISO 8601."""
    return dt.astimezone(timezone.utc).isoformat() if dt else None


# Imported at the end to register the routes on the blueprint (avoids circular import)
from . import auth, courses, sessions  # noqa: E402,F401
