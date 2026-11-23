"""Courses of the logged-in user + PDF upload.

FR-01 POST   /api/courses
FR-02 GET    /api/courses            and  GET /api/courses/<id>
FR-03 PUT    /api/courses/<id>
FR-04 DELETE /api/courses/<id>
FR-05 POST   /api/courses/<id>/pdf
BR-01 name + teacher cannot repeat for the same user
BR-02 the PDF is validated by its content on the server
"""
import logging
import os
import uuid

from flask import current_app, jsonify, request
from flask_jwt_extended import jwt_required
from psycopg2 import errors
from werkzeug.utils import secure_filename

import database as db
from validations import PDF_MIME, normalize_text, validate_pdf

from .api import api, current_user_id, error_response, iso, request_data

log = logging.getLogger(__name__)

MAX_TEXT = 100
MSG_DUPLICATE = "a course with this name and teacher already exists"
MSG_NOT_FOUND = "course not found"
COLUMNS = "id, name, teacher, created_at, updated_at"


def _serialize(c: dict) -> dict:
    return {
        "id": c["id"],
        "name": c["name"],
        "teacher": c["teacher"],
        "created_at": iso(c["created_at"]),
        "updated_at": iso(c["updated_at"]),
    }


def _read_fields() -> tuple[str, str, str | None]:
    d = request_data()
    name = normalize_text(d.get("name"))
    teacher = normalize_text(d.get("teacher"))
    if not name or not teacher:
        return name, teacher, "required fields: name, teacher"
    if len(name) > MAX_TEXT or len(teacher) > MAX_TEXT:
        return name, teacher, f"name and teacher must have at most {MAX_TEXT} characters"
    return name, teacher, None


def _duplicate_exists(cur, user_id: int, name: str, teacher: str, ignore_id: int | None = None) -> bool:
    # Same rule as the ux_courses_user_name_teacher index (case-insensitive)
    cur.execute(
        "SELECT 1 FROM courses WHERE user_id = %s AND LOWER(name) = LOWER(%s) "
        "AND LOWER(teacher) = LOWER(%s) AND id <> %s",
        (user_id, name, teacher, ignore_id or 0),
    )
    return cur.fetchone() is not None


def user_course(cur, course_id: int, user_id: int) -> dict | None:
    """Another user's course is treated as nonexistent (404), without revealing that it exists."""
    cur.execute(f"SELECT {COLUMNS} FROM courses WHERE id = %s AND user_id = %s", (course_id, user_id))
    return cur.fetchone()


# ---------------------------------------------------------------------
# CRUD
# ---------------------------------------------------------------------
@api.get("/courses")
@jwt_required()
def list_courses():
    # Explicit ICU collation: with the "C" collation (and with the musl of postgres:16-alpine)
    # "Álgebra" comes after "Física" (bug B-11 found during Check)
    with db.transaction() as cur:
        cur.execute(
            f'SELECT {COLUMNS} FROM courses WHERE user_id = %s ORDER BY name COLLATE "und-x-icu", id',
            (current_user_id(),),
        )
        rows = cur.fetchall()
    return jsonify(status="success", courses=[_serialize(c) for c in rows])


@api.get("/courses/<int:course_id>")
@jwt_required()
def get_course(course_id: int):
    with db.transaction() as cur:
        c = user_course(cur, course_id, current_user_id())
    if not c:
        return error_response(MSG_NOT_FOUND, 404)
    return jsonify(status="success", course=_serialize(c))


@api.post("/courses")
@jwt_required()
def create_course():
    name, teacher, msg = _read_fields()
    if msg:
        return error_response(msg, 400)
    uid = current_user_id()
    try:
        with db.transaction() as cur:
            if _duplicate_exists(cur, uid, name, teacher):
                return error_response(MSG_DUPLICATE, 409)
            cur.execute(
                f"INSERT INTO courses (user_id, name, teacher) VALUES (%s, %s, %s) RETURNING {COLUMNS}",
                (uid, name, teacher),
            )
            new = cur.fetchone()
    except errors.UniqueViolation:  # two identical requests at the same time
        return error_response(MSG_DUPLICATE, 409)
    return jsonify(status="success", course=_serialize(new)), 201


@api.put("/courses/<int:course_id>")
@jwt_required()
def update_course(course_id: int):
    name, teacher, msg = _read_fields()
    if msg:
        return error_response(msg, 400)
    uid = current_user_id()
    try:
        with db.transaction() as cur:
            if not user_course(cur, course_id, uid):
                return error_response(MSG_NOT_FOUND, 404)
            if _duplicate_exists(cur, uid, name, teacher, ignore_id=course_id):
                return error_response(MSG_DUPLICATE, 409)
            cur.execute(
                f"UPDATE courses SET name = %s, teacher = %s, updated_at = NOW() "
                f"WHERE id = %s AND user_id = %s RETURNING {COLUMNS}",
                (name, teacher, course_id, uid),
            )
            updated = cur.fetchone()
    except errors.UniqueViolation:
        return error_response(MSG_DUPLICATE, 409)
    return jsonify(status="success", course=_serialize(updated))


@api.delete("/courses/<int:course_id>")
@jwt_required()
def delete_course(course_id: int):
    uid = current_user_id()
    with db.transaction() as cur:
        if not user_course(cur, course_id, uid):
            return error_response(MSG_NOT_FOUND, 404)
        cur.execute("SELECT id FROM sessions WHERE course_id = %s AND ended_at IS NULL", (course_id,))
        open_session = cur.fetchone()
        if open_session:
            return error_response(
                "finish the session in progress before deleting the course", 409, session_id=open_session["id"]
            )
        cur.execute("SELECT stored_name FROM pdfs WHERE course_id = %s", (course_id,))
        files = [r["stored_name"] for r in cur.fetchall()]
        # ON DELETE CASCADE removes the course's PDFs, sessions and pauses
        cur.execute("DELETE FROM courses WHERE id = %s AND user_id = %s", (course_id, uid))

    # Only delete from disk after the commit
    folder = os.path.join(current_app.config["UPLOAD_DIR"], str(uid))
    for name in files:
        try:
            os.remove(os.path.join(folder, name))
        except FileNotFoundError:
            pass
        except OSError as e:
            log.warning("Could not remove %s: %s", name, e)
    return jsonify(status="success")


# ---------------------------------------------------------------------
# PDF upload
# ---------------------------------------------------------------------
@api.post("/courses/<int:course_id>/pdf")
@jwt_required()
def upload_pdf(course_id: int):
    uid = current_user_id()
    with db.transaction() as cur:
        if not user_course(cur, course_id, uid):
            return error_response(MSG_NOT_FOUND, 404)

    file = request.files.get("file")  # size limited by MAX_CONTENT_LENGTH (413)
    if file is None or not file.filename:
        return error_response("send the file in the multipart field 'file'", 400)
    content = file.read()
    if not content:
        return error_response("empty file", 400)

    msg = validate_pdf(content, file.mimetype)  # BR-02
    if msg:
        return error_response(msg, 415)

    original_name = (secure_filename(file.filename) or "document.pdf")[:255]
    stored_name = f"{uuid.uuid4().hex}.pdf"  # never uses the client's name on disk
    folder = os.path.join(current_app.config["UPLOAD_DIR"], str(uid))
    os.makedirs(folder, exist_ok=True)
    path = os.path.join(folder, stored_name)

    with open(path, "wb") as f:
        f.write(content)
    try:
        with db.transaction() as cur:
            cur.execute(
                "INSERT INTO pdfs (course_id, original_name, stored_name, size_bytes, mime) "
                "VALUES (%s, %s, %s, %s, %s) RETURNING id, created_at",
                (course_id, original_name, stored_name, len(content), PDF_MIME),
            )
            row = cur.fetchone()
    except errors.ForeignKeyViolation:  # course deleted during the upload
        os.remove(path)
        return error_response(MSG_NOT_FOUND, 404)
    except Exception:
        os.remove(path)  # do not leave an orphan file if the database fails
        raise

    return jsonify(
        status="success",
        pdf={
            "id": row["id"],
            "course_id": course_id,
            "original_name": original_name,
            "size_bytes": len(content),
            "mime": PDF_MIME,
            "created_at": iso(row["created_at"]),
        },
    ), 201
