"""/api/courses endpoints."""
import pytest


# ---------------------------- FR-01 ----------------------------
@pytest.mark.req("FR-01")
def test_create_course_returns_201_with_data(client, auth):
    r = client.post("/api/courses", json={"name": "  Cálculo   I ", "teacher": "Prof. Ana"}, headers=auth)
    assert r.status_code == 201
    c = r.get_json()["course"]
    assert c["id"] > 0 and c["name"] == "Cálculo I" and c["teacher"] == "Prof. Ana"
    assert c["created_at"].endswith("+00:00")


@pytest.mark.req("FR-01")
def test_create_course_accepts_form(client, auth):
    r = client.post("/api/courses", data={"name": "Física", "teacher": "Prof. Bia"}, headers=auth)
    assert r.status_code == 201


@pytest.mark.req("FR-01", "NFR-02")
@pytest.mark.parametrize(
    "body",
    [{}, {"name": "Física"}, {"teacher": "Bia"}, {"name": "   ", "teacher": "Bia"}, {"name": "x" * 101, "teacher": "Bia"}, {"name": 5, "teacher": "Bia"}],
    ids=["empty", "no-teacher", "no-name", "blank-name", "long-name", "non-text-name"],
)
def test_create_invalid_course_returns_400(client, auth, body):
    r = client.post("/api/courses", json=body, headers=auth)
    assert r.status_code == 400 and r.get_json()["status"] == "error"


# ---------------------------- BR-01 ----------------------------
@pytest.mark.req("BR-01", "FR-01")
@pytest.mark.parametrize(
    "name,teacher",
    [("Cálculo I", "Prof. Ana"), ("cálculo i", "PROF. ANA"), ("  Cálculo    I", "Prof.  Ana ")],
    ids=["identical", "uppercase", "spaces"],
)
def test_duplicate_course_for_same_user_returns_409(client, auth, create_course, name, teacher):
    create_course(auth, "Cálculo I", "Prof. Ana")
    r = client.post("/api/courses", json={"name": name, "teacher": teacher}, headers=auth)
    assert r.status_code == 409
    assert r.get_json()["error"] == "a course with this name and teacher already exists"


@pytest.mark.req("BR-01")
def test_same_name_with_another_teacher_is_allowed(client, auth, create_course):
    create_course(auth, "Cálculo I", "Prof. Ana")
    r = client.post("/api/courses", json={"name": "Cálculo I", "teacher": "Prof. Carlos"}, headers=auth)
    assert r.status_code == 201


@pytest.mark.req("BR-01", "NFR-01")
def test_same_course_for_different_users_is_allowed(client, auth, auth_b, create_course):
    create_course(auth, "Cálculo I", "Prof. Ana")
    r = client.post("/api/courses", json={"name": "Cálculo I", "teacher": "Prof. Ana"}, headers=auth_b)
    assert r.status_code == 201


@pytest.mark.req("BR-01")
def test_unique_index_enforces_br01_even_without_the_api(db, client, auth, create_course):
    """Defense in depth: even a direct INSERT (or a race between requests) is blocked."""
    import psycopg2

    create_course(auth, "Cálculo I", "Prof. Ana")
    with pytest.raises(psycopg2.errors.UniqueViolation), db.cursor() as cur:
        cur.execute("INSERT INTO courses (user_id, name, teacher) VALUES (1, 'CÁLCULO I', 'prof. ana')")


# ---------------------------- FR-02 ----------------------------
@pytest.mark.req("FR-02", "NFR-01")
def test_list_returns_only_user_courses_sorted(client, auth, auth_b, create_course):
    create_course(auth, "Física", "Prof. Bia")
    create_course(auth, "Álgebra", "Prof. Caio")
    create_course(auth_b, "Química", "Prof. Davi")
    r = client.get("/api/courses", headers=auth)
    assert r.status_code == 200
    assert [c["name"] for c in r.get_json()["courses"]] == ["Álgebra", "Física"]


@pytest.mark.req("FR-02")
def test_list_without_courses_returns_empty_list(client, auth):
    assert client.get("/api/courses", headers=auth).get_json()["courses"] == []


@pytest.mark.req("FR-02", "NFR-01")
def test_get_by_id_and_isolation(client, auth, auth_b, create_course):
    c = create_course(auth)
    assert client.get(f"/api/courses/{c['id']}", headers=auth).get_json()["course"]["id"] == c["id"]
    assert client.get(f"/api/courses/{c['id']}", headers=auth_b).status_code == 404
    assert client.get("/api/courses/999", headers=auth).status_code == 404


# ---------------------------- FR-03 ----------------------------
@pytest.mark.req("FR-03")
def test_update_course(client, auth, create_course):
    c = create_course(auth)
    r = client.put(f"/api/courses/{c['id']}", json={"name": "Cálculo II", "teacher": "Prof. Ana"}, headers=auth)
    assert r.status_code == 200
    new = r.get_json()["course"]
    assert new["name"] == "Cálculo II" and new["updated_at"] >= c["updated_at"]


@pytest.mark.req("FR-03", "BR-01")
def test_update_keeping_same_data_is_not_a_duplicate(client, auth, create_course):
    c = create_course(auth, "Cálculo I", "Prof. Ana")
    r = client.put(f"/api/courses/{c['id']}", json={"name": "CÁLCULO I", "teacher": "Prof. Ana"}, headers=auth)
    assert r.status_code == 200


@pytest.mark.req("FR-03", "BR-01")
def test_update_to_another_course_data_returns_409(client, auth, create_course):
    create_course(auth, "Cálculo I", "Prof. Ana")
    c2 = create_course(auth, "Física", "Prof. Bia")
    r = client.put(f"/api/courses/{c2['id']}", json={"name": "Cálculo I", "teacher": "Prof. Ana"}, headers=auth)
    assert r.status_code == 409


@pytest.mark.req("FR-03", "NFR-01")
def test_update_another_users_course_returns_404(client, auth, auth_b, create_course):
    c = create_course(auth)
    r = client.put(f"/api/courses/{c['id']}", json={"name": "Hack", "teacher": "X"}, headers=auth_b)
    assert r.status_code == 404
    assert client.get(f"/api/courses/{c['id']}", headers=auth).get_json()["course"]["name"] == "Cálculo I"


@pytest.mark.req("FR-03", "NFR-02")
def test_update_with_invalid_data_returns_400(client, auth, create_course):
    c = create_course(auth)
    assert client.put(f"/api/courses/{c['id']}", json={"name": "Name only"}, headers=auth).status_code == 400


# ---------------------------- FR-04 ----------------------------
@pytest.mark.req("FR-04")
def test_delete_course(client, auth, create_course):
    c = create_course(auth)
    assert client.delete(f"/api/courses/{c['id']}", headers=auth).status_code == 200
    assert client.get(f"/api/courses/{c['id']}", headers=auth).status_code == 404
    assert client.delete(f"/api/courses/{c['id']}", headers=auth).status_code == 404


@pytest.mark.req("FR-04", "NFR-01")
def test_delete_another_users_course_returns_404(client, auth, auth_b, create_course):
    c = create_course(auth)
    assert client.delete(f"/api/courses/{c['id']}", headers=auth_b).status_code == 404
    assert client.get(f"/api/courses/{c['id']}", headers=auth).status_code == 200


@pytest.mark.req("FR-04", "FR-06")
def test_does_not_delete_course_with_session_in_progress(client, auth, create_course):
    c = create_course(auth)
    s = client.post("/api/sessions", json={"action": "start", "course_id": c["id"]}, headers=auth).get_json()["session"]
    r = client.delete(f"/api/courses/{c['id']}", headers=auth)
    assert r.status_code == 409 and r.get_json()["session_id"] == s["id"]


@pytest.mark.req("FR-04")
def test_delete_course_removes_its_finished_sessions(client, auth, create_course):
    c = create_course(auth)
    s = client.post("/api/sessions", json={"action": "start", "course_id": c["id"]}, headers=auth).get_json()["session"]
    client.post("/api/sessions", json={"action": "finish", "session_id": s["id"]}, headers=auth)
    assert client.delete(f"/api/courses/{c['id']}", headers=auth).status_code == 200
    assert client.get("/api/sessions", headers=auth).get_json()["sessions"] == []


# ---------------------------- NFR-01 ----------------------------
@pytest.mark.req("NFR-01")
@pytest.mark.parametrize(
    "method,route",
    [("get", "/api/courses"), ("post", "/api/courses"), ("get", "/api/courses/1"),
     ("put", "/api/courses/1"), ("delete", "/api/courses/1"), ("post", "/api/courses/1/pdf"),
     ("get", "/api/sessions"), ("post", "/api/sessions")],
)
def test_protected_routes_require_token(client, method, route):
    r = getattr(client, method)(route)
    assert r.status_code == 401 and r.get_json()["status"] == "error"
