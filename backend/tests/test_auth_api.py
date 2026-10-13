"""API של הרשמה, התחברות, refresh, logout ו-/me."""

from unittest.mock import patch
from uuid import UUID, uuid4

import pytest
import sqlalchemy as sa
from app import create_app
from app.auth.require_role import require_role
from app.config import Config
from app.infrastructure.tables import event_store, metadata, rm_users
from app.reference.institutions import INSTITUTIONS
from flask import jsonify
from flask_jwt_extended import decode_token
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool


@pytest.fixture
def engine():
    db = create_engine("sqlite://", poolclass=StaticPool, connect_args={"check_same_thread": False})
    metadata.create_all(db)
    yield db
    db.dispose()


def _config(engine, **overrides):
    class TestConfig(Config):
        DB_ENGINE = engine
        JWT_SECRET = "unit-test-jwt-secret-0123456789abcd"
        RATELIMIT_ENABLED = False
        TESTING = True

    for key, value in overrides.items():
        setattr(TestConfig, key, value)
    return TestConfig


@pytest.fixture
def client(engine):
    app = create_app(_config(engine))
    app.extensions["test_engine"] = engine
    return app.test_client()


def _register(client, **overrides):
    body = {
        "fullName": "נועה לוי",
        "email": "noa@mail.com",
        "phone": "0501234567",
        "password": "Secret12",
        "role": "INVESTOR",
    }
    body.update(overrides)
    return client.post("/api/auth/register", json=body, headers={"Idempotency-Key": str(uuid4())})


def _login(client, email="noa@mail.com", password="Secret12"):
    return client.post("/api/auth/login", json={"email": email, "password": password})


def test_register_investor_returns_id_and_version(client):
    resp = _register(client)
    assert resp.status_code == 201
    body = resp.get_json()
    assert body["version"] == 1
    assert UUID(body["id"])


def test_duplicate_email_returns_409_and_no_second_event(client):
    assert _register(client).status_code == 201
    duplicate = _register(client)
    assert duplicate.status_code == 409
    assert duplicate.get_json()["error"]["code"] == "EMAIL_EXISTS"
    assert _count(client, event_store) == 1


def test_email_case_and_spaces_are_the_same_user(client):
    assert _register(client, email="  Noa@Mail.com ").status_code == 201
    duplicate = _register(client, email="noa@mail.com")
    assert duplicate.status_code == 409
    assert duplicate.get_json()["error"]["code"] == "EMAIL_EXISTS"
    login = _login(client, email="NOA@mail.com")
    assert login.status_code == 200
    with Session(client.application.extensions["test_engine"]) as session:
        email = session.execute(sa.select(rm_users.c.email)).scalar_one()
    assert email == "noa@mail.com"


def test_parallel_unique_violation_returns_409(client):
    assert _register(client).status_code == 201
    with patch("app.commands.register_user.email_exists", return_value=False):
        resp = _register(client, email="noa@mail.com")
    assert resp.status_code == 409
    assert resp.get_json()["error"]["code"] == "EMAIL_EXISTS"
    assert _count(client, rm_users) == 1
    assert _count(client, event_store) == 1


def test_wrong_password_and_unknown_email_return_401(client):
    assert _register(client).status_code == 201
    wrong = _login(client, password="Other12x")
    missing = _login(client, email="missing@mail.com")
    assert wrong.status_code == 401
    assert missing.status_code == 401
    assert wrong.get_json()["error"]["message"] == "אימייל או סיסמה שגויים"
    assert missing.get_json()["error"]["message"] == wrong.get_json()["error"]["message"]


def test_me_with_access_token(client):
    assert _register(client).status_code == 201
    login = _login(client)
    assert login.status_code == 200
    body = login.get_json()
    assert body["user"] == {"id": body["user"]["id"], "role": "INVESTOR", "fullName": "נועה לוי"}
    with client.application.app_context():
        access = decode_token(body["accessToken"])
        refresh = decode_token(body["refreshToken"])
    assert access["role"] == "INVESTOR"
    assert access["institution_id"] is None
    assert access["exp"] - access["iat"] == 30 * 60
    assert refresh["exp"] - refresh["iat"] == 7 * 24 * 60 * 60
    me = client.get("/api/auth/me", headers={"Authorization": f"Bearer {body['accessToken']}"})
    assert me.status_code == 200
    profile = me.get_json()
    assert profile["email"] == "noa@mail.com"
    assert profile["role"] == "INVESTOR"
    assert profile["status"] == "ACTIVE"
    assert "password_hash" not in profile
    assert client.get("/api/auth/me").status_code == 401


def test_agent_institution_must_be_in_the_catalog(client):
    unknown = _register(client, role="AGENT", institutionId=str(uuid4()), licenseNo="LIC-1")
    assert unknown.status_code == 400
    assert "institutionId" in unknown.get_json()["error"]["fields"]
    institution = INSTITUTIONS[0]
    created = _register(
        client,
        email="agent@mail.com",
        role="AGENT",
        institutionId=str(institution.id),
        licenseNo="LIC-1",
    )
    assert created.status_code == 201
    login = _login(client, email="agent@mail.com")
    with client.application.app_context():
        claims = decode_token(login.get_json()["accessToken"])
    assert claims["role"] == "AGENT"
    assert claims["institution_id"] == str(institution.id)
    me = client.get("/api/auth/me", headers={"Authorization": f"Bearer {login.get_json()['accessToken']}"})
    assert me.get_json()["institutionId"] == str(institution.id)


def test_institutions_query_returns_the_catalog(client):
    resp = client.get("/api/institutions")
    assert resp.status_code == 200
    items = resp.get_json()["items"]
    assert [item["name"] for item in items] == [item.name for item in INSTITUTIONS]
    assert items[0]["id"] == str(INSTITUTIONS[0].id)


def test_refresh_rotates_and_logout_revokes(client):
    assert _register(client).status_code == 201
    login = _login(client).get_json()
    refreshed = client.post("/api/auth/refresh", json={"refreshToken": login["refreshToken"]})
    assert refreshed.status_code == 200
    new_tokens = refreshed.get_json()
    assert new_tokens["accessToken"] != login["accessToken"]
    stale = client.post("/api/auth/refresh", json={"refreshToken": login["refreshToken"]})
    assert stale.status_code == 401
    logout = client.post(
        "/api/auth/logout",
        json={"refreshToken": new_tokens["refreshToken"]},
        headers={"Authorization": f"Bearer {new_tokens['accessToken']}"},
    )
    assert logout.status_code == 204
    after = client.post("/api/auth/refresh", json={"refreshToken": new_tokens["refreshToken"]})
    assert after.status_code == 401


def test_investor_token_is_forbidden_on_agent_route(client):
    @client.application.get("/api/agent-only")
    @require_role("AGENT")
    def _agent_only():
        return jsonify({"ok": True})

    assert _register(client).status_code == 201
    token = _login(client).get_json()["accessToken"]
    resp = client.get("/api/agent-only", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 403
    assert resp.get_json()["error"]["code"] == "FORBIDDEN"


def test_login_is_blocked_after_five_failures(engine):
    app = create_app(_config(engine, RATELIMIT_ENABLED=True))
    client = app.test_client()
    email = f"lock-{uuid4()}@mail.com"
    for _ in range(5):
        resp = client.post("/api/auth/login", json={"email": email, "password": "Wrong12"})
        assert resp.status_code == 401
    blocked = client.post("/api/auth/login", json={"email": email, "password": "Wrong12"})
    assert blocked.status_code == 429
    assert blocked.get_json()["error"]["code"] == "RATE_LIMITED"


def test_jwt_secret_warning(capsys):
    class Placeholder(Config):
        JWT_SECRET = "change-me"
        RATELIMIT_ENABLED = False

    create_app(Placeholder)
    assert "change-me" in capsys.readouterr().err

    class Missing(Config):
        JWT_SECRET = ""
        RATELIMIT_ENABLED = False

    create_app(Missing)
    assert "JWT_SECRET" in capsys.readouterr().err


def _count(client, table) -> int:
    with Session(client.application.extensions["test_engine"]) as session:
        return session.execute(sa.select(sa.func.count()).select_from(table)).scalar_one()
