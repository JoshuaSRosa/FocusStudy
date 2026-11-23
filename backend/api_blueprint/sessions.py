"""Focus sessions (Pomodoro).

FR-06 POST /api/sessions                    body: {"action": ..., ...}
FR-07 GET  /api/sessions?course=<id>        (optional filter)
BR-03 start/end/pauses use the server clock; timestamps sent by the client are ignored
BR-04 effective time = total duration - pauses  (focus.calculate_focus_time)

Lifecycle (state machine):

    start ──> in_progress ──pause──> paused
                 ^   │                 │
                 │   └────finish────┐  │
                 └──────resume──────┼──┘
                                    v
                                finished   (an open pause is closed at the end)
"""
from flask import jsonify, request
from flask_jwt_extended import jwt_required
from psycopg2 import errors

import clock
import database as db
from focus import calculate_focus_time

from .api import api, current_user_id, error_response, iso, request_data, to_positive_int
from .courses import MSG_NOT_FOUND, user_course

ACTIONS = ("start", "pause", "resume", "finish")
MSG_SESSION_NOT_FOUND = "session not found"
MSG_ALREADY_OPEN = "there is already a session in progress; finish it first"

# Which states each action can start from
TRANSITIONS = {
    "pause": {"in_progress"},
    "resume": {"paused"},
    "finish": {"in_progress", "paused"},
}


def _serialize(s: dict, pauses: list[dict], now) -> dict:
    # Open session: times calculated "until now" (the client can display a timer)
    end_ref = s["ended_at"] or max(now, s["started_at"])
    t = calculate_focus_time(s["started_at"], end_ref, [(p["started_at"], p["ended_at"]) for p in pauses])
    return {
        "id": s["id"],
        "course_id": s["course_id"],
        "status": s["status"],
        "started_at": iso(s["started_at"]),
        "ended_at": iso(s["ended_at"]),
        "total_duration_seconds": t.total_seconds,
        "paused_seconds": t.paused_seconds,
        "effective_seconds": t.effective_seconds,
        "pauses": [{"started_at": iso(p["started_at"]), "ended_at": iso(p["ended_at"])} for p in pauses],
    }


def _pauses(cur, session_id: int) -> list[dict]:
    cur.execute(
        "SELECT session_id, started_at, ended_at FROM pauses WHERE session_id = %s ORDER BY started_at",
        (session_id,),
    )
    return cur.fetchall()


@api.post("/sessions")
@jwt_required()
def session_action():
    d = request_data()
    action = str(d.get("action") or "").strip().lower()
    if action not in ACTIONS:
        return error_response(f"field 'action' must be one of: {', '.join(ACTIONS)}", 400)

    uid = current_user_id()
    now = clock.now()  # BR-03: any "started_at"/"ended_at" sent by the client is ignored

    if action == "start":
        return _start(uid, d, now)

    session_id = to_positive_int(d.get("session_id"))
    if session_id is None:
        return error_response("field 'session_id' is required (positive integer)", 400)

    with db.transaction() as cur:
        # FOR UPDATE: two simultaneous actions on the same session are serialized
        cur.execute("SELECT * FROM sessions WHERE id = %s AND user_id = %s FOR UPDATE", (session_id, uid))
        s = cur.fetchone()
        if not s:
            return error_response(MSG_SESSION_NOT_FOUND, 404)
        if s["status"] not in TRANSITIONS[action]:
            return error_response(f"cannot '{action}' a session with status '{s['status']}'", 409)

        pauses = _pauses(cur, session_id)
        # Protection against a clock that "goes back" (NTP adjustment): never before the last event
        last = max([s["started_at"]] + [p["started_at"] for p in pauses] + [p["ended_at"] for p in pauses if p["ended_at"]])
        now = max(now, last)

        if action == "pause":
            cur.execute("INSERT INTO pauses (session_id, started_at) VALUES (%s, %s)", (session_id, now))
            new_status = "paused"
        elif action == "resume":
            cur.execute("UPDATE pauses SET ended_at = %s WHERE session_id = %s AND ended_at IS NULL", (now, session_id))
            new_status = "in_progress"
        else:  # finish
            cur.execute("UPDATE pauses SET ended_at = %s WHERE session_id = %s AND ended_at IS NULL", (now, session_id))
            new_status = "finished"

        pauses = _pauses(cur, session_id)
        if new_status == "finished":
            t = calculate_focus_time(s["started_at"], now, [(p["started_at"], p["ended_at"]) for p in pauses])
            cur.execute(
                "UPDATE sessions SET status = 'finished', ended_at = %s, effective_seconds = %s WHERE id = %s RETURNING *",
                (now, t.effective_seconds, session_id),
            )
        else:
            cur.execute("UPDATE sessions SET status = %s WHERE id = %s RETURNING *", (new_status, session_id))
        s = cur.fetchone()

    return jsonify(status="success", session=_serialize(s, pauses, now)), 200


def _start(uid: int, d: dict, now):
    course_id = to_positive_int(d.get("course_id"))
    if course_id is None:
        return error_response("field 'course_id' is required (positive integer)", 400)
    try:
        with db.transaction() as cur:
            if not user_course(cur, course_id, uid):
                return error_response(MSG_NOT_FOUND, 404)
            cur.execute("SELECT id FROM sessions WHERE user_id = %s AND ended_at IS NULL", (uid,))
            open_session = cur.fetchone()
            if open_session:
                return error_response(MSG_ALREADY_OPEN, 409, session_id=open_session["id"])
            cur.execute(
                "INSERT INTO sessions (user_id, course_id, status, started_at) "
                "VALUES (%s, %s, 'in_progress', %s) RETURNING *",
                (uid, course_id, now),
            )
            s = cur.fetchone()
    except errors.UniqueViolation:  # two simultaneous "start"s
        return error_response(MSG_ALREADY_OPEN, 409)
    return jsonify(status="success", session=_serialize(s, [], now)), 201


@api.get("/sessions")
@jwt_required()
def history():
    uid = current_user_id()
    course_filter = request.args.get("course")
    course_id = None
    if course_filter is not None:
        course_id = to_positive_int(course_filter)
        if course_id is None:
            return error_response("parameter 'course' must be a positive integer", 400)

    with db.transaction() as cur:
        if course_id is not None and not user_course(cur, course_id, uid):
            return error_response(MSG_NOT_FOUND, 404)

        sql = "SELECT * FROM sessions WHERE user_id = %s"
        params: list = [uid]
        if course_id is not None:
            sql += " AND course_id = %s"
            params.append(course_id)
        cur.execute(sql + " ORDER BY started_at DESC, id DESC", params)
        sessions = cur.fetchall()

        pauses_by_session: dict[int, list[dict]] = {s["id"]: [] for s in sessions}
        if sessions:
            cur.execute(
                "SELECT session_id, started_at, ended_at FROM pauses WHERE session_id = ANY(%s) ORDER BY started_at",
                (list(pauses_by_session),),
            )
            for p in cur.fetchall():
                pauses_by_session[p["session_id"]].append(p)

    now = clock.now()
    items = [_serialize(s, pauses_by_session[s["id"]], now) for s in sessions]
    finished = [i for i in items if i["status"] == "finished"]
    return jsonify(
        status="success",
        sessions=items,
        summary={
            "session_count": len(items),
            "finished_sessions": len(finished),
            "total_effective_seconds": sum(i["effective_seconds"] for i in finished),
        },
    )
