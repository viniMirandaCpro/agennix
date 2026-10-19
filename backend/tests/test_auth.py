"""Historia 5.1: tela de login com autenticacao (Flask-Login)."""
from app.extensions import db
from tests.conftest import PASSWORD


def login(client, email="admin@teste.dev", password=PASSWORD):
    return client.post("/api/auth/login", json={"email": email, "password": password})


def test_login_ok_returns_user_and_tenant_timezone(client, admin):
    r = login(client)
    assert r.status_code == 200
    assert r.json["user"]["email"] == "admin@teste.dev"
    assert r.json["tenant"]["timezone"] == "America/Sao_Paulo"
    db.session.refresh(admin)
    assert admin.last_login_at is not None


def test_login_wrong_password_is_401_with_message(client, admin):
    r = login(client, password="errada")
    assert r.status_code == 401
    assert r.json["message"] == "E-mail ou senha incorretos"


def test_login_inactive_user_is_401(client, admin):
    admin.active = False
    db.session.commit()
    assert login(client).status_code == 401


def test_login_missing_fields_is_400(client):
    assert client.post("/api/auth/login", json={}).status_code == 400


def test_me_without_session_is_401(client):
    assert client.get("/api/auth/me").status_code == 401


def test_logout_ends_session(client, admin):
    login(client)
    assert client.get("/api/auth/me").status_code == 200
    assert client.post("/api/auth/logout").status_code == 200
    assert client.get("/api/auth/me").status_code == 401


def test_login_non_text_credentials_is_400(client, admin):
    assert client.post("/api/auth/login", json={"email": 5, "password": PASSWORD}).status_code == 400
