"""Authentication endpoints. Cover the Sprint 1 bugs found in PDCA (B-xx in docs/pdca-sprint2.md)."""
import pytest

from conftest import PASSWORD, register_and_login

USER = {"username": "joao_1", "email": "joao@focus.com", "name": "João Silva", "password": PASSWORD}


@pytest.mark.req("FR-08")
def test_health(client):
    assert client.get("/api/health").get_json() == {"status": "ok"}


@pytest.mark.req("FR-08")
def test_register_success_via_form_stores_salted_hash(client, db):
    r = client.post("/api/register", data=USER)
    assert r.status_code == 201
    body = r.get_json()
    assert body["status"] == "success" and body["user"]["name"] == "João Silva"
    with db.cursor() as cur:
        cur.execute("SELECT password_hash FROM users WHERE username = 'joao_1'")
        password_hash = cur.fetchone()[0]
    assert PASSWORD not in password_hash and not password_hash.isalnum()  # not plain text nor sha256 hex


@pytest.mark.req("FR-08")
def test_register_accepts_json_and_optional_program(client, db):
    r = client.post("/api/register", json={**USER, "program": "Software Engineering"})
    assert r.status_code == 201
    with db.cursor() as cur:
        cur.execute("SELECT program FROM users WHERE username = 'joao_1'")
        assert cur.fetchone()[0] == "Software Engineering"


@pytest.mark.req("FR-08", "NFR-02")
def test_register_missing_fields_returns_400_json(client):
    """B-02: used to return 500 (jsonify of a set)."""
    r = client.post("/api/register", data={"username": "joao_1"})
    assert r.status_code == 400
    assert r.get_json()["status"] == "error"


@pytest.mark.req("FR-08", "NFR-02")
@pytest.mark.parametrize(
    "field,value",
    [("username", "a"), ("email", "invalid"), ("name", "Joao"), ("password", "weak")],
)
def test_register_invalid_data_returns_400(client, field, value):
    assert client.post("/api/register", data={**USER, field: value}).status_code == 400


@pytest.mark.req("FR-08", "NFR-02")
@pytest.mark.parametrize(
    "change,message",
    [
        ({"email": "other@focus.com"}, "username already registered"),
        ({"username": "other_1"}, "email already registered"),
        ({}, "username and email already registered"),
        ({"username": "JOAO_1", "email": "x@focus.com"}, "username already registered"),  # case-insensitive
    ],
)
def test_register_duplicate_returns_409(client, change, message):
    """B-05: the old duplicate check swapped parameters and compared a dict with a str."""
    client.post("/api/register", data=USER)
    r = client.post("/api/register", data={**USER, **change})
    assert r.status_code == 409
    assert r.get_json()["error"] == message


@pytest.mark.req("FR-09")
@pytest.mark.parametrize("field,value", [("user", "joao@focus.com"), ("user", "joao_1"), ("username", "JOAO_1"), ("email", "joao@focus.com")])
def test_login_by_email_or_username(client, field, value):
    client.post("/api/register", data=USER)
    r = client.post("/api/login", data={field: value, "password": PASSWORD})
    assert r.status_code == 200
    body = r.get_json()
    assert body["status"] == "success" and body["logged_as"] == "joao_1" and body["access_token"]


@pytest.mark.req("FR-09", "NFR-02")
@pytest.mark.parametrize("user,password", [("joao_1", "Wrong@123"), ("nobody", PASSWORD)])
def test_invalid_login_returns_401_with_same_message(client, user, password):
    client.post("/api/register", data=USER)
    r = client.post("/api/login", data={"user": user, "password": password})
    assert r.status_code == 401
    assert r.get_json()["error"] == "invalid username or password"


@pytest.mark.req("FR-09")
def test_login_without_credentials_returns_400(client):
    assert client.post("/api/login", data={}).status_code == 400


@pytest.mark.req("FR-09")
def test_login_with_valid_token_does_not_require_password(client):
    """Behavior described in instructions.txt; the password used to be required even with a token."""
    headers = register_and_login(client, "joao_2")
    r = client.post("/api/login", headers=headers)
    assert r.status_code == 200 and r.get_json()["logged_as"] == "joao_2"


@pytest.mark.req("NFR-01", "NFR-02")
def test_invalid_token_returns_401_json(client):
    r = client.post("/api/login", headers={"Authorization": "Bearer abc.def.ghi"})
    assert r.status_code == 401 and r.get_json()["status"] == "error"


@pytest.mark.req("NFR-02")
def test_unknown_route_returns_404_json(client):
    r = client.get("/api/does-not-exist")
    assert r.status_code == 404 and r.get_json()["status"] == "error"
