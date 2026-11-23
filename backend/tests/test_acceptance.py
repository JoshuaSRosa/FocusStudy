"""VAL-01 - Acceptance test (Validation, ISO/IEC 12207).

User story:
  "As a student, I want to record my study sessions for a course,
   with pauses, so that I know how much time I actually studied."

Acceptance criteria (docs/validacao-sprint2.md):
  AC1 - I can create the course I study;
  AC2 - I can attach the course material (PDF);
  AC3 - I can start, pause, resume and finish a Pomodoro;
  AC4 - the time shown excludes the pauses;
  AC5 - I can see the course history with the total studied;
  AC6 - another student cannot see my data.

This test runs the flow as the frontend would. It is automated evidence,
but formal VALIDATION is only complete at the Sprint Review, with the
team/PO confirming the criteria (see docs/validacao-sprint2.md).
"""
import io

import pytest

from conftest import PASSWORD


@pytest.mark.req("VAL-01")
def test_student_records_pomodoros_and_sees_effective_time_in_history(client, fake_clock):
    # Registration and login (Sprint 1)
    client.post("/api/register", data={"username": "maria_st", "email": "maria@focus.com", "name": "Maria Souza", "password": PASSWORD})
    token = client.post("/api/login", data={"user": "maria@focus.com", "password": PASSWORD}).get_json()["access_token"]
    h = {"Authorization": f"Bearer {token}"}

    # AC1
    r = client.post("/api/courses", json={"name": "Estruturas de Dados", "teacher": "Prof. Lima"}, headers=h)
    assert r.status_code == 201
    course = r.get_json()["course"]

    # AC2
    pdf = b"%PDF-1.7\n%...\ntrailer<<>>\n%%EOF"
    r = client.post(
        f"/api/courses/{course['id']}/pdf",
        data={"file": (io.BytesIO(pdf), "list1.pdf", "application/pdf")},
        headers=h,
        content_type="multipart/form-data",
    )
    assert r.status_code == 201

    # AC3 + AC4: two 25-minute Pomodoros with a 5-minute break between them
    s = client.post("/api/sessions", json={"action": "start", "course_id": course["id"]}, headers=h).get_json()["session"]
    fake_clock.advance(minutes=25)
    client.post("/api/sessions", json={"action": "pause", "session_id": s["id"]}, headers=h)
    fake_clock.advance(minutes=5)
    client.post("/api/sessions", json={"action": "resume", "session_id": s["id"]}, headers=h)
    fake_clock.advance(minutes=25)
    r = client.post("/api/sessions", json={"action": "finish", "session_id": s["id"]}, headers=h)
    assert r.status_code == 200
    assert r.get_json()["session"]["effective_seconds"] == 50 * 60

    # AC5
    hist = client.get(f"/api/sessions?course={course['id']}", headers=h).get_json()
    assert hist["summary"]["total_effective_seconds"] == 50 * 60
    assert hist["sessions"][0]["paused_seconds"] == 5 * 60

    # AC6
    client.post("/api/register", data={"username": "pedro_st", "email": "pedro@focus.com", "name": "Pedro Lima", "password": PASSWORD})
    t2 = client.post("/api/login", data={"user": "pedro_st", "password": PASSWORD}).get_json()["access_token"]
    h2 = {"Authorization": f"Bearer {t2}"}
    assert client.get("/api/courses", headers=h2).get_json()["courses"] == []
    assert client.get("/api/sessions", headers=h2).get_json()["sessions"] == []
