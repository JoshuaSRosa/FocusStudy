"""/api/sessions endpoints. The server clock is controlled by `fake_clock`."""
import pytest

START_ISO = "2026-11-23T14:00:00+00:00"


def act(client, headers, action, **fields):
    return client.post("/api/sessions", json={"action": action, **fields}, headers=headers)


@pytest.fixture
def course(auth, create_course):
    return create_course(auth)


@pytest.fixture
def start(client, auth, course, fake_clock):
    def _start():
        r = act(client, auth, "start", course_id=course["id"])
        assert r.status_code == 201, r.get_json()
        return r.get_json()["session"]

    return _start


# ---------------------------- FR-06 / BR-03 ----------------------------
@pytest.mark.req("FR-06", "BR-03")
def test_start_session_uses_server_time(client, auth, course, fake_clock):
    r = act(client, auth, "start", course_id=course["id"])
    assert r.status_code == 201
    s = r.get_json()["session"]
    assert s["status"] == "in_progress" and s["started_at"] == START_ISO and s["ended_at"] is None
    assert s["course_id"] == course["id"]


@pytest.mark.req("BR-03")
def test_timestamps_sent_by_client_are_ignored(client, auth, course, fake_clock):
    r = act(client, auth, "start", course_id=course["id"], started_at="2020-01-01T00:00:00Z")
    s = r.get_json()["session"]
    assert s["started_at"] == START_ISO
    fake_clock.advance(minutes=25)
    r = act(client, auth, "finish", session_id=s["id"], ended_at="2030-01-01T00:00:00Z", effective_seconds=99999)
    s = r.get_json()["session"]
    assert s["ended_at"] == "2026-11-23T14:25:00+00:00" and s["effective_seconds"] == 1500


@pytest.mark.req("BR-03")
def test_default_clock_is_server_clock_in_utc(client, auth, course):
    """Without the fake clock: the start lies between before and after the request (UTC)."""
    from datetime import datetime, timezone

    before = datetime.now(timezone.utc)
    s = act(client, auth, "start", course_id=course["id"]).get_json()["session"]
    after = datetime.now(timezone.utc)
    assert before <= datetime.fromisoformat(s["started_at"]) <= after


@pytest.mark.req("FR-06", "BR-04")
def test_finish_without_pauses(client, auth, start, fake_clock):
    s = start()
    fake_clock.advance(minutes=25)
    r = act(client, auth, "finish", session_id=s["id"])
    assert r.status_code == 200
    s = r.get_json()["session"]
    assert s["status"] == "finished"
    assert (s["total_duration_seconds"], s["paused_seconds"], s["effective_seconds"]) == (1500, 0, 1500)


@pytest.mark.req("FR-06", "BR-03", "BR-04")
def test_full_cycle_with_pauses_subtracts_paused_time(client, auth, start, fake_clock, db):
    s = start()
    fake_clock.advance(minutes=25)
    assert act(client, auth, "pause", session_id=s["id"]).get_json()["session"]["status"] == "paused"
    fake_clock.advance(minutes=5)
    assert act(client, auth, "resume", session_id=s["id"]).get_json()["session"]["status"] == "in_progress"
    fake_clock.advance(minutes=25)
    act(client, auth, "pause", session_id=s["id"])
    fake_clock.advance(minutes=10)
    act(client, auth, "resume", session_id=s["id"])
    fake_clock.advance(minutes=5)
    s = act(client, auth, "finish", session_id=s["id"]).get_json()["session"]

    assert s["total_duration_seconds"] == 70 * 60
    assert s["paused_seconds"] == 15 * 60
    assert s["effective_seconds"] == 55 * 60
    assert s["pauses"] == [
        {"started_at": "2026-11-23T14:25:00+00:00", "ended_at": "2026-11-23T14:30:00+00:00"},
        {"started_at": "2026-11-23T14:55:00+00:00", "ended_at": "2026-11-23T15:05:00+00:00"},
    ]
    with db.cursor() as cur:  # value persisted for reports
        cur.execute("SELECT effective_seconds FROM sessions WHERE id = %s", (s["id"],))
        assert cur.fetchone()[0] == 55 * 60


@pytest.mark.req("FR-06", "BR-04")
def test_finishing_paused_session_closes_the_pause(client, auth, start, fake_clock):
    s = start()
    fake_clock.advance(minutes=20)
    act(client, auth, "pause", session_id=s["id"])
    fake_clock.advance(minutes=10)
    s = act(client, auth, "finish", session_id=s["id"]).get_json()["session"]
    assert s["pauses"][0]["ended_at"] == s["ended_at"]
    assert s["effective_seconds"] == 20 * 60


@pytest.mark.req("BR-03", "BR-04")
def test_clock_going_back_does_not_produce_negative_time(client, auth, start, fake_clock):
    s = start()
    fake_clock.advance(minutes=-3)  # e.g. NTP adjustment
    r = act(client, auth, "finish", session_id=s["id"])
    assert r.status_code == 200 and r.get_json()["session"]["effective_seconds"] == 0


@pytest.mark.req("FR-06", "NFR-02")
@pytest.mark.parametrize(
    "sequence,invalid_action",
    [([], "resume"), (["pause"], "pause"), (["finish"], "pause"), (["finish"], "resume"), (["finish"], "finish")],
)
def test_invalid_transitions_return_409(client, auth, start, sequence, invalid_action):
    s = start()
    for step in sequence:
        assert act(client, auth, step, session_id=s["id"]).status_code == 200
    r = act(client, auth, invalid_action, session_id=s["id"])
    assert r.status_code == 409 and r.get_json()["status"] == "error"


@pytest.mark.req("FR-06")
def test_only_one_open_session_per_user(client, auth, start, create_course, fake_clock):
    s = start()
    other = create_course(auth, "Física", "Prof. Bia")
    r = act(client, auth, "start", course_id=other["id"])
    assert r.status_code == 409 and r.get_json()["session_id"] == s["id"]
    act(client, auth, "finish", session_id=s["id"])
    assert act(client, auth, "start", course_id=other["id"]).status_code == 201


@pytest.mark.req("FR-06", "NFR-02")
@pytest.mark.parametrize(
    "body",
    [{}, {"action": "fly"}, {"action": "start"}, {"action": "start", "course_id": "abc"}, {"action": "start", "course_id": -1},
     {"action": "start", "course_id": True}, {"action": "pause"}, {"action": "finish", "session_id": "x"}],
)
def test_invalid_request_returns_400(client, auth, body):
    r = client.post("/api/sessions", json=body, headers=auth)
    assert r.status_code == 400 and r.get_json()["status"] == "error"


@pytest.mark.req("FR-06", "NFR-01")
def test_cannot_start_on_another_users_course(client, auth, auth_b, course):
    assert act(client, auth_b, "start", course_id=course["id"]).status_code == 404
    assert act(client, auth, "start", course_id=999).status_code == 404


@pytest.mark.req("FR-06", "NFR-01")
def test_cannot_change_another_users_session(client, auth, auth_b, start):
    s = start()
    assert act(client, auth_b, "finish", session_id=s["id"]).status_code == 404
    assert act(client, auth, "finish", session_id=s["id"]).status_code == 200


@pytest.mark.req("FR-06", "BR-04")
def test_open_session_reports_time_until_now(client, auth, start, fake_clock):
    s = start()
    fake_clock.advance(minutes=10)
    act(client, auth, "pause", session_id=s["id"])
    fake_clock.advance(minutes=4)
    item = client.get("/api/sessions", headers=auth).get_json()["sessions"][0]
    assert item["status"] == "paused"
    assert (item["total_duration_seconds"], item["paused_seconds"], item["effective_seconds"]) == (840, 240, 600)


# ---------------------------- FR-07 ----------------------------
@pytest.mark.req("FR-07")
def test_history_filtered_by_course_with_summary(client, auth, create_course, fake_clock):
    calc = create_course(auth, "Cálculo I", "Prof. Ana")
    phys = create_course(auth, "Física", "Prof. Bia")
    for c, minutes in [(calc, 25), (phys, 30), (calc, 50)]:
        s = act(client, auth, "start", course_id=c["id"]).get_json()["session"]
        fake_clock.advance(minutes=minutes)
        act(client, auth, "finish", session_id=s["id"])
        fake_clock.advance(minutes=5)
    open_s = act(client, auth, "start", course_id=calc["id"]).get_json()["session"]

    body = client.get(f"/api/sessions?course={calc['id']}", headers=auth).get_json()
    assert [s["course_id"] for s in body["sessions"]] == [calc["id"]] * 3
    assert body["sessions"][0]["id"] == open_s["id"]  # most recent first
    assert body["summary"] == {"session_count": 3, "finished_sessions": 2, "total_effective_seconds": 75 * 60}

    everything = client.get("/api/sessions", headers=auth).get_json()
    assert everything["summary"]["session_count"] == 4
    assert everything["summary"]["total_effective_seconds"] == 105 * 60


@pytest.mark.req("FR-07")
def test_empty_history(client, auth, course):
    body = client.get(f"/api/sessions?course={course['id']}", headers=auth).get_json()
    assert body["sessions"] == [] and body["summary"]["total_effective_seconds"] == 0


@pytest.mark.req("FR-07", "NFR-01")
def test_history_isolated_per_user(client, auth, auth_b, start, fake_clock, course):
    start()
    assert client.get("/api/sessions", headers=auth_b).get_json()["sessions"] == []
    assert client.get(f"/api/sessions?course={course['id']}", headers=auth_b).status_code == 404


@pytest.mark.req("FR-07", "NFR-02")
@pytest.mark.parametrize("value", ["abc", "0", "-2", ""])
def test_history_invalid_filter_returns_400(client, auth, value):
    assert client.get(f"/api/sessions?course={value}", headers=auth).status_code == 400
