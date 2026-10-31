"""לידים, הצעות והתראות: TC-11, TC-12 ו-404 לגוף אחר."""

from datetime import date
from uuid import UUID, uuid4

import sqlalchemy as sa
from app import create_app
from app.bootstrap import build_command_bus
from app.commands.assessments import CompleteAssessment, StartAssessment
from app.config import Config
from app.infrastructure.tables import metadata, rm_leads, rm_requests
from app.projections.leads import rebuild_agent_views
from app.queries.assessments import pending_requests, request_for_assessment
from app.reference.institutions import INSTITUTIONS
from goalvest_core.goals.dates import add_months
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool


def _client():
    engine = create_engine("sqlite://", poolclass=StaticPool, connect_args={"check_same_thread": False})
    metadata.create_all(engine)

    class TestConfig(Config):
        DB_ENGINE = engine
        JWT_SECRET = "unit-test-jwt-secret-0123456789abcd"
        RATELIMIT_ENABLED = False
        TESTING = True

    app = create_app(TestConfig)
    app.extensions["test_engine"] = engine
    return app.test_client(), engine


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


def _token(client, email):
    response = client.post("/api/auth/login", json={"email": email, "password": "Secret12"})
    assert response.status_code == 200
    return response.get_json()["accessToken"]


def _investor(client):
    assert _register(client).status_code == 201
    token = _token(client, "noa@mail.com")
    answers = {
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
    assert client.post("/api/investor/risk-assessment", json=answers, headers=_headers(token)).status_code == 201
    goal = {
        "type": "APARTMENT",
        "title": "דירה",
        "initialAmount": "150000.00",
        "monthlyDeposit": "3000.00",
        "targetAmount": "400000.00",
        "targetDate": add_months(date.today(), 48).isoformat(),
        "flexibility": "YEAR_1",
        "liquidityNeed": "PARTIAL",
        "excludedChannels": [],
        "preferredChannels": [],
        "preferredInstitutions": [],
    }
    created = client.post("/api/investor/goals", json=goal, headers=_headers(token))
    assert created.status_code == 201
    submitted = client.post(
        "/api/requests",
        json={"goalId": created.get_json()["id"], "consentShareContact": True},
        headers=_headers(token),
    )
    assert submitted.status_code == 201
    return token, submitted.get_json()["id"]


def _agent(client, email, institution):
    created = _register(
        client,
        email=email,
        fullName="סוכן דמו",
        phone="0500000000",
        role="AGENT",
        institutionId=str(institution.id),
        licenseNo="LIC-9",
    )
    assert created.status_code == 201, created.get_json()
    return _token(client, email)


def _product(client, token, name="מסלול א"):
    body = {
        "type": "HISHTALMUT",
        "name": name,
        "track": "כללי",
        "feeDeposit": "0.00",
        "feeAssets": "0.80",
        "return1y": "7.20",
        "return3y": "6.10",
        "return5y": "5.40",
        "stdDev": "8.50",
        "riskLevel": 3,
        "liquidity": "PARTIAL",
        "liquidityTerms": "הנזילות חלקית.",
        "taxNotes": "לפי הדין.",
        "minDeposit": "0.00",
        "description": "קרן להמחשה.",
    }
    created = client.post("/api/agent/products", json=body, headers=_headers(token))
    assert created.status_code == 201, created.get_json()
    return created.get_json()["id"]


def _evaluate(client, request_id, product_id):
    with Session(client.application.extensions["test_engine"]) as session:
        row = request_for_assessment(session, UUID(request_id))
        bus = build_command_bus(session, client.application.extensions["projections"])
        started = bus.dispatch(StartAssessment(
            command_id=uuid4(),
            request_id=UUID(request_id),
            expected_version=row["version"],
            agent_run_id=uuid4(),
            model="fake",
        ))
        bus.dispatch(CompleteAssessment(
            command_id=uuid4(),
            request_id=UUID(request_id),
            expected_version=started.version,
            assessment={
                "overall_score": 78,
                "channel_scores": {"capital_market": 20, "hishtalmut": 70, "gemel_policy": 40},
                "allocation": {"capital_market": 20, "hishtalmut": 80, "gemel_policy": 0},
                "recommended_products": [{
                    "product_id": product_id,
                    "fit_score": 88,
                    "reason": "מתאים יותר לטווח היעד",
                }],
                "rationale": "כדאי לשקול את המסלול הזה.",
                "risk_flags": [],
                "sources": [{"type": "web", "title": "מקור", "url": "https://example.com", "excerpt": "ציטוט"}],
                "model": "fake",
                "duration_ms": 15,
            },
        ))


def test_agent_lead_flow_covers_rejection_allocation_and_other_institution(client=None):
    client, engine = _client()
    try:
        investor, request_id = _investor(client)
        mine = INSTITUTIONS[0]
        other = INSTITUTIONS[1]
        agent = _agent(client, "agent-a@mail.com", mine)
        outsider = _agent(client, "agent-b@mail.com", other)
        product_id = _product(client, agent)
        _evaluate(client, request_id, product_id)

        hidden = client.get(f"/api/agent/leads/{request_id}", headers=_headers(outsider))
        assert hidden.status_code == 404

        visible = client.get(f"/api/agent/leads/{request_id}", headers=_headers(agent))
        assert visible.status_code == 200
        body = visible.get_json()
        assert body["investor"]["displayName"] == "נועה לוי"
        assert body["investor"]["email"] == "noa@mail.com"
        assert body["assessment"]["overallScore"] == 78

        claimed = client.post(f"/api/agent/leads/{request_id}/claim", headers=_headers(agent))
        assert claimed.status_code == 201

        still_empty = client.post(
            f"/api/agent/leads/{request_id}/assessment/reject",
            json={},
            headers=_headers(agent),
        )
        assert still_empty.status_code == 400

        short = client.post(
            f"/api/agent/leads/{request_id}/offers",
            json={"items": [{"productId": product_id, "percent": 90}], "message": "הצעה"},
            headers=_headers(agent),
        )
        assert short.status_code == 422
        assert short.get_json()["error"]["code"] == "ALLOCATION_NOT_100"

        sent = client.post(
            f"/api/agent/leads/{request_id}/offers",
            json={"items": [{"productId": product_id, "percent": 100}], "message": "כדאי לשקול את המסלול."},
            headers=_headers(agent),
        )
        assert sent.status_code == 201, sent.get_json()
        offer_id = sent.get_json()["id"]

        offers = client.get("/api/investor/offers", headers=_headers(investor))
        assert offers.status_code == 200
        assert offers.get_json()["items"][0]["offerId"] == offer_id
        unread = client.get("/api/notifications/unread-count", headers=_headers(investor))
        assert unread.get_json()["count"] == 1

        accepted = client.post(f"/api/investor/offers/{offer_id}/accept", headers=_headers(investor))
        assert accepted.status_code == 201
        dashboard = client.get("/api/agent/dashboard", headers=_headers(agent))
        assert dashboard.get_json()["offersAccepted"] == 1
        assert dashboard.get_json()["conversionRate"] == "100.0"

        with Session(engine) as session:
            session.execute(sa.delete(rm_leads))
            session.commit()
            assert rebuild_agent_views(session) == 1
            session.commit()
            status = session.execute(sa.select(rm_leads.c.status)).scalar_one()
        assert status == "ACCEPTED"

        listed = client.get("/api/agent/leads?status=ACCEPTED", headers=_headers(agent))
        assert listed.get_json()["total"] == 1
        interest = client.get("/api/agent/dashboard/product-interest", headers=_headers(agent))
        row = interest.get_json()["items"][0]
        assert row["recommended"] == 1
        assert row["offers"] == 1
        assert row["accepted"] == 1
    finally:
        engine.dispose()


def test_contact_is_hidden_without_consent_and_reevaluation_returns_to_the_queue():
    client, engine = _client()
    try:
        _investor_token, request_id = _investor(client)
        agent = _agent(client, "agent-a@mail.com", INSTITUTIONS[0])
        product_id = _product(client, agent)
        with Session(engine) as session:
            session.execute(
                sa.update(rm_requests)
                .where(rm_requests.c.request_id == UUID(request_id))
                .values(consent_share_contact=False)
            )
            session.commit()
        _evaluate(client, request_id, product_id)
        details = client.get(f"/api/agent/leads/{request_id}", headers=_headers(agent))
        investor = details.get_json()["investor"]
        assert investor["displayName"] == "משקיע אנונימי"
        assert investor["email"] is None
        assert investor["phone"] is None

        assert client.post(f"/api/agent/leads/{request_id}/claim", headers=_headers(agent)).status_code == 201
        again = client.post(
            f"/api/agent/leads/{request_id}/reevaluate",
            json={"reason": "חסר מסלול"},
            headers=_headers(agent),
        )
        assert again.status_code == 201
        with Session(engine) as session:
            from datetime import UTC, datetime

            queued = pending_requests(session, datetime.now(UTC))
        assert UUID(request_id) in {row["request_id"] for row in queued}
    finally:
        engine.dispose()
