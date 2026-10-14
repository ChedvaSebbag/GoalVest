"""API של פרופיל, יעדים ובקשות: 201, 400, 403, 404 ו-422."""

from datetime import date
from uuid import UUID, uuid4

import pytest
import sqlalchemy as sa
from app import create_app
from app.config import Config
from app.infrastructure.tables import metadata, rm_goals, rm_requests
from app.reference.institutions import INSTITUTIONS
from goalvest_core.goals.dates import add_months
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool


@pytest.fixture
def client():
    engine = create_engine("sqlite://", poolclass=StaticPool, connect_args={"check_same_thread": False})
    metadata.create_all(engine)

    class TestConfig(Config):
        DB_ENGINE = engine
        JWT_SECRET = "unit-test-jwt-secret-0123456789abcd"
        RATELIMIT_ENABLED = False
        TESTING = True

    app = create_app(TestConfig)
    app.extensions["test_engine"] = engine
    yield app.test_client()
    engine.dispose()


def _headers(token=None):
    headers = {"Idempotency-Key": str(uuid4())}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def _register(client, **overrides):
    body = {
        "fullName": "נועה לוי",
        "email": "noa@mail.com",
        "phone": "0501234567",
        "password": "Secret12",
        "role": "INVESTOR",
    }
    body.update(overrides)
    return client.post("/api/auth/register", json=body, headers=_headers())


def _token(client, email="noa@mail.com", password="Secret12"):
    response = client.post("/api/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200
    return response.get_json()["accessToken"]


def _answers():
    return {
        "answers": {
            "birthYear": 1994,
            "horizon": "Y6_TO_10",
            "dropReaction": "WAIT",
            "experience": "FUNDS",
            "incomeStability": "SALARIED",
            "emergencyFund": "YES",
            "maritalStatus": "MARRIED",
            "monthlyIncomeRange": "FROM_20K_TO_35K",
            "existingProducts": ["HISHTALMUT"],
        }
    }


def _goal(**overrides):
    body = {
        "type": "APARTMENT",
        "title": "דירה",
        "initialAmount": "150000.00",
        "monthlyDeposit": "3000.00",
        "targetAmount": "400000.00",
        "targetDate": add_months(date.today(), 24).isoformat(),
        "flexibility": "YEAR_1",
        "liquidityNeed": "PARTIAL",
        "excludedChannels": [],
        "preferredChannels": ["GEMEL_POLICY"],
        "preferredInstitutions": [],
    }
    body.update(overrides)
    return body


def _assess(client, token):
    return client.post("/api/investor/risk-assessment", json=_answers(), headers=_headers(token))


def _ready(client, email="noa@mail.com"):
    assert _register(client, email=email).status_code == 201
    token = _token(client, email=email)
    assert _assess(client, token).status_code == 201
    created = client.post("/api/investor/goals", json=_goal(), headers=_headers(token))
    assert created.status_code == 201, created.get_json()
    return token, created.get_json()["id"]


def _submit(client, token, goal_id, consent=True):
    return client.post(
        "/api/requests",
        json={"goalId": goal_id, "consentShareContact": consent},
        headers=_headers(token),
    )


def _set_status(client, request_id, status):
    with Session(client.application.extensions["test_engine"]) as session:
        session.execute(
            sa.update(rm_requests).where(rm_requests.c.request_id == UUID(request_id)).values(status=status)
        )
        session.commit()


def test_assessment_goal_request_and_timeline(client):
    token, goal_id = _ready(client)
    profile = client.get("/api/investor/profile", headers=_headers(token))
    assert profile.status_code == 200
    assert profile.get_json()["riskLabel"] == "מאוזן-צמיחה"
    submitted = _submit(client, token, goal_id)
    assert submitted.status_code == 201
    request_id = submitted.get_json()["id"]
    listed = client.get("/api/investor/goals", headers=_headers(token))
    assert listed.get_json()["items"][0]["requestStatus"] == "SUBMITTED"
    details = client.get(f"/api/investor/goals/{goal_id}", headers=_headers(token))
    assert details.status_code == 200
    assert details.get_json()["title"] == "דירה"
    timeline = client.get(f"/api/requests/{request_id}/timeline", headers=_headers(token))
    assert timeline.status_code == 200
    assert timeline.get_json()["items"][0]["displayText"] == "הבקשה הוגשה"


def test_past_target_date_is_400(client):
    assert _register(client).status_code == 201
    token = _token(client)
    response = client.post(
        "/api/investor/goals",
        json=_goal(targetDate="2020-01-01"),
        headers=_headers(token),
    )
    assert response.status_code == 400
    assert "targetDate" in response.get_json()["error"]["fields"]


def test_second_request_is_422_and_missing_profile_is_422(client):
    token, goal_id = _ready(client)
    assert _submit(client, token, goal_id).status_code == 201
    again = _submit(client, token, goal_id)
    assert again.status_code == 422
    assert again.get_json()["error"]["code"] == "ACTIVE_REQUEST_EXISTS"

    assert _register(client, email="dana@mail.com").status_code == 201
    other = _token(client, email="dana@mail.com")
    created = client.post("/api/investor/goals", json=_goal(), headers=_headers(other))
    assert created.status_code == 201
    missing = _submit(client, other, created.get_json()["id"])
    assert missing.status_code == 422
    assert missing.get_json()["error"]["code"] == "RISK_PROFILE_REQUIRED"


def test_agent_is_forbidden(client):
    institution = str(INSTITUTIONS[0].id)
    registered = _register(
        client,
        email="yael@mail.com",
        role="AGENT",
        institutionId=institution,
        licenseNo="LIC-9",
        fullName="יעל כהן",
    )
    assert registered.status_code == 201
    token = _token(client, email="yael@mail.com")
    response = client.get("/api/investor/goals", headers=_headers(token))
    assert response.status_code == 403


def test_other_investor_gets_404(client):
    token, goal_id = _ready(client)
    request_id = _submit(client, token, goal_id).get_json()["id"]
    assert _register(client, email="dana@mail.com").status_code == 201
    other = _token(client, email="dana@mail.com")
    assert client.get(f"/api/investor/goals/{goal_id}", headers=_headers(other)).status_code == 404
    assert client.put(
        f"/api/investor/goals/{goal_id}",
        json={**_goal(title="דירה אחרת"), "consentShareContact": True},
        headers=_headers(other),
    ).status_code == 404
    assert client.delete(f"/api/investor/goals/{goal_id}", headers=_headers(other)).status_code == 404
    assert client.get(f"/api/requests/{request_id}/timeline", headers=_headers(other)).status_code == 404
    cancelled = client.post(f"/api/requests/{request_id}/cancel", json={"reason": "לא"}, headers=_headers(other))
    assert cancelled.status_code == 404


def test_cancel_from_evaluated_and_review(client):
    token, goal_id = _ready(client)
    first = _submit(client, token, goal_id).get_json()["id"]
    _set_status(client, first, "AI_EVALUATED")
    evaluated = client.post(f"/api/requests/{first}/cancel", json={"reason": "שינוי"}, headers=_headers(token))
    assert evaluated.status_code == 201

    second_goal = client.post("/api/investor/goals", json=_goal(title="רכב"), headers=_headers(token))
    second = _submit(client, token, second_goal.get_json()["id"]).get_json()["id"]
    _set_status(client, second, "IN_REVIEW")
    review = client.post(f"/api/requests/{second}/cancel", json={}, headers=_headers(token))
    assert review.status_code == 201


def test_edit_and_archive_while_processing_are_422(client):
    token, goal_id = _ready(client)
    request_id = _submit(client, token, goal_id).get_json()["id"]
    _set_status(client, request_id, "AI_PROCESSING")
    edited = client.put(
        f"/api/investor/goals/{goal_id}",
        json={**_goal(title="דירה מעודכנת"), "consentShareContact": True},
        headers=_headers(token),
    )
    assert edited.status_code == 422
    assert edited.get_json()["error"]["code"] == "REQUEST_IN_PROCESSING"
    archived = client.delete(f"/api/investor/goals/{goal_id}", headers=_headers(token))
    assert archived.status_code == 422
    assert archived.get_json()["error"]["code"] == "REQUEST_IN_PROCESSING"
    with Session(client.application.extensions["test_engine"]) as session:
        title = session.execute(sa.select(rm_goals.c.title)).scalar_one()
        status = session.execute(sa.select(rm_goals.c.status)).scalar_one()
    assert title == "דירה"
    assert status == "ACTIVE"


def test_edit_with_active_request_replaces_it(client):
    token, goal_id = _ready(client)
    _submit(client, token, goal_id)
    updated = client.put(
        f"/api/investor/goals/{goal_id}",
        json={**_goal(title="דירה גדולה"), "consentShareContact": True},
        headers=_headers(token),
    )
    assert updated.status_code == 201
    details = client.get(f"/api/investor/goals/{goal_id}", headers=_headers(token)).get_json()
    assert details["title"] == "דירה גדולה"
    timeline = client.get(
        f"/api/requests/{details['activeRequestId']}/timeline",
        headers=_headers(token),
    ).get_json()["items"]
    assert timeline[0]["displayText"] == "הבקשה הוגשה"
    with Session(client.application.extensions["test_engine"]) as session:
        statuses = session.execute(sa.select(rm_requests.c.status)).scalars().all()
    assert sorted(statuses) == ["CANCELLED", "SUBMITTED"]
