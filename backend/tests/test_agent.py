"""הערכת AI: חוקים, ולידציה, נעילה, כשל תשתית והשלכה לטבלאות."""

from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from unittest.mock import patch
from uuid import uuid4

import pytest
import sqlalchemy as sa
from app import create_app
from app.bootstrap import build_command_bus, build_dispatcher
from app.commands.assessments import StartAssessment
from app.config import Config
from app.infrastructure.event_store import EventStoreRepository
from app.infrastructure.tables import rm_assessments, rm_products, rm_request_timeline, rm_requests
from app.queries.assessments import pending_requests, request_for_assessment, stuck_requests
from app.queries.candidates import find_candidate_products
from app.queries.goals import get_goal
from goalvest_core import BusinessRuleViolation, ConcurrencyError
from goalvest_core.goals import Goal
from goalvest_core.goals.dates import add_months
from goalvest_core.requests import InvestmentRequest, RequestStatus

from agent.errors import InfrastructureError
from agent.loop import process_batch, process_request
from agent.pipeline import Services, run_assessment
from agent.privacy import assert_public, market_queries, sensitive_terms
from agent.schema import DISCLAIMER, Allocation, ChannelScores, ModelAssessment, RecommendedProduct, Source
from agent.scoring import overall_score
from agent.suitability import evaluate, load_rules
from agent.validate import problems
from mcp_tools.tax import load_tax_rules

TODAY = date(2026, 10, 14)
NOW = datetime(2026, 10, 14, 12, 0, tzinfo=UTC)


class QuietConfig(Config):
    DB_CONNECTION_STRING = ""
    OLLAMA_BASE_URL = "http://127.0.0.1:9"
    CHROMA_URL = "http://127.0.0.1:9"
    HEALTH_TIMEOUT_SECONDS = 0.2
    JWT_SECRET = "unit-test-jwt-secret-0123456789abcd"
    RATELIMIT_ENABLED = False


def _snapshot(**changes):
    target = TODAY + timedelta(days=changes.get("years", 4) * 365)
    goal = {
        "type": changes.get("goal_type", "APARTMENT"),
        "title": "דירה",
        "target_date": target.isoformat(),
        "liquidity_need": "NONE",
        "excluded_channels": changes.get("excluded", []),
        "initial_amount": "150000.00",
        "monthly_deposit": "3000.00",
        "target_amount": "400000.00",
    }
    return {
        "goal": goal,
        "risk": {
            "score": changes.get("score", 3),
            "label": changes.get("label", "מאוזן"),
            "answers": {
                "birth_year": changes.get("birth", 1990),
                "emergency_fund": changes.get("emergency", "YES"),
                "existing_products": changes.get("products", ["NONE"]),
                "email": "noa@mail.com",
            },
        },
    }


def _rules():
    return evaluate(_snapshot(), today=TODAY, rules=load_rules(), tax_rules=load_tax_rules())


def _product_id():
    return uuid4()


def _services(snapshot=None, *, mode="chain", deep=None, synthesize=None, products=None, web=None):
    product = str(_product_id()) if products is None else None
    catalog = products if products is not None else [{
        "product_id": product,
        "name": "גמל כללי",
        "type": "GEMEL_INVESTMENT",
        "channel": "gemel_policy",
        "institution_name": "גוף לדוגמה",
        "track": "כללי",
        "symbol": None,
        "risk_level": 4,
        "liquidity": "HIGH",
        "fee_assets": "0.60",
        "fee_deposit": "0",
    }]
    calls = {"deep": 0, "synth": 0}

    def deep_run(prompt):
        calls["deep"] += 1
        if deep is not None:
            return deep(prompt)
        raise AssertionError("deep")

    def synth(prompt):
        calls["synth"] += 1
        if synthesize is not None:
            return synthesize(prompt)
        return "לא json"

    rules = load_rules()
    services = Services(
        mode=mode,
        model_name="fake",
        load_products=lambda _snapshot: catalog,
        search_knowledge=lambda _query, _collection: [{
            "title": "כללי מס",
            "document_id": str(uuid4()),
            "excerpt": "תקופת הנעילה והמס מתוך המאגר.",
        }],
        search_web=web or (lambda _query: [{
            "title": "ריבית בנק ישראל",
            "url": "https://example.com/rate",
            "excerpt": "הריבית הנוכחית.",
        }]),
        run_tools=lambda _snapshot, _products: {"tax": [], "volatility": [], "fees": [], "growth": []},
        synthesize=synth,
        rules=rules,
        tax_rules=load_tax_rules(),
        deep_run=deep_run,
        bonus=int(rules["retirement_bonus"]),
    )
    return services, calls, catalog


def _submit(session, snapshot=None):
    investor_id = uuid4()
    goal = Goal()
    goal.create(
        investor_id=investor_id,
        today=TODAY,
        known_institutions=set(),
        goal_type="APARTMENT",
        title="דירה",
        initial_amount=Decimal(150000),
        monthly_deposit=Decimal(3000),
        target_amount=Decimal(400000),
        target_date=add_months(TODAY, 48),
        flexibility="YEAR_1",
        liquidity_need="NONE",
        excluded_channels=[],
        preferred_channels=[],
        preferred_institutions=[],
    )
    request = InvestmentRequest()
    request.submit(
        goal_id=goal.aggregate_id,
        investor_id=investor_id,
        snapshot=snapshot or _snapshot(),
        consent_share_contact=True,
    )
    repo = EventStoreRepository(session, build_dispatcher())
    repo.append(goal.aggregate_id, 0, goal.uncommitted_events)
    repo.append(request.aggregate_id, 0, request.uncommitted_events)
    session.commit()
    return repo, request, investor_id, goal


def test_lockup_caps_hishtalmut_without_an_existing_fund():
    result = _rules()
    assert result.score_caps["hishtalmut"] <= 40
    assert any(flag["code"] == "LOCKUP_EXCEEDS_HORIZON" and flag["severity"] == "high" for flag in result.flags)
    kept = evaluate(
        _snapshot(products=["HISHTALMUT"]),
        today=TODAY,
        rules=load_rules(),
        tax_rules=load_tax_rules(),
    )
    assert "hishtalmut" not in kept.score_caps


def test_unrealistic_goal_adds_a_severe_numeric_flag():
    snapshot = _snapshot(years=2)
    snapshot["goal"]["target_amount"] = "2000000.00"
    snapshot["goal"]["initial_amount"] = "10000.00"
    snapshot["goal"]["monthly_deposit"] = "100.00"
    result = evaluate(snapshot, today=TODAY, rules=load_rules(), tax_rules=load_tax_rules())
    flag = next(item for item in result.flags if item["code"] == "GOAL_UNREALISTIC")
    assert flag["severity"] == "high"
    assert "8%" in flag["text"]
    assert "70%" in flag["text"]
    assert "2000000" in flag["text"]
    ordinary = _rules()
    assert all(item["code"] != "GOAL_UNREALISTIC" for item in ordinary.flags)


def test_excluded_capital_market_is_zero():
    result = evaluate(
        _snapshot(excluded=["CAPITAL_MARKET"]),
        today=TODAY,
        rules=load_rules(),
        tax_rules=load_tax_rules(),
    )
    assert result.score_caps["capital_market"] == 0
    assert result.allocation_caps["capital_market"] == 0
    assert any(flag["code"] == "EXCLUDED_CHANNEL" for flag in result.flags)


def test_output_must_match_rules_candidates_and_sources():
    suitability = _rules()
    product = uuid4()
    output = ModelAssessment(
        channel_scores=ChannelScores(capital_market=40, hishtalmut=90, gemel_policy=50),
        allocation=Allocation(capital_market=20, hishtalmut=30, gemel_policy=50),
        recommended_products=[RecommendedProduct(product_id=product, fit_score=50, reason="מתאים יותר")],
        rationale="כדאי לשקול " * 30,
        risk_flags=[],
        sources=[
            Source(type="rag", title="מסמך", excerpt="ציטוט"),
            Source(type="web", title="אתר", url="https://example.com/rate"),
        ],
    )
    assert any("hishtalmut" in item for item in problems(output, suitability, {str(product)}))
    outsider = ModelAssessment(
        channel_scores=ChannelScores(capital_market=40, hishtalmut=30, gemel_policy=50),
        allocation=Allocation(capital_market=20, hishtalmut=30, gemel_policy=50),
        recommended_products=[RecommendedProduct(product_id=uuid4(), fit_score=50, reason="מתאים יותר")],
        rationale="כדאי לשקול " * 30,
        sources=[
            Source(type="rag", title="מסמך", excerpt="ציטוט"),
            Source(type="tool", title="מחשבון"),
        ],
    )
    found = problems(outsider, suitability, {str(product)})
    assert any("מועמד" in item for item in found)
    assert any("web" in item for item in found)


def test_overall_score_is_computed_with_a_severe_penalty():
    score = overall_score(
        {"capital_market": 50, "hishtalmut": 40, "gemel_policy": 60},
        {"capital_market": 20, "hishtalmut": 0, "gemel_policy": 80},
        [{"severity": "high"}],
        10,
    )
    assert score == 48


def test_chain_uses_baseline_when_the_model_format_fails_and_respects_lockup():
    services, calls, _catalog = _services()
    outcome = run_assessment(_snapshot(), services, today=TODAY)
    assert outcome.ok
    assert calls["deep"] == 0
    assert calls["synth"] == 2
    assert outcome.payload["channel_scores"]["hishtalmut"] <= 40
    assert outcome.payload["disclaimer"] == DISCLAIMER
    assert any(flag["code"] == "LOCKUP_EXCEEDS_HORIZON" for flag in outcome.payload["risk_flags"])
    assert any(source["type"] == "rag" for source in outcome.payload["sources"])
    assert any(source["type"] == "web" for source in outcome.payload["sources"])
    assert "baseline" in outcome.trace.notes


def test_deep_format_failure_falls_back_to_the_chain():
    services, calls, _catalog = _services(mode="deep", deep=lambda _prompt: "לא json")
    outcome = run_assessment(_snapshot(), services, today=TODAY)
    assert outcome.ok
    assert calls["deep"] == 2
    assert calls["synth"] == 2


def test_web_queries_do_not_include_personal_amounts():
    snapshot = _snapshot()
    products = [{"institution_name": "גוף לדוגמה", "track": "כללי", "name": "מסלול"}]
    queries = market_queries(products)
    banned = sensitive_terms(snapshot)
    for query in queries:
        assert_public(query, banned)
    with pytest.raises(ValueError):
        assert_public(f"ריבית {banned[0]}", banned)


def test_two_agents_cannot_lock_the_same_version(session):
    _repo, request, _investor, _goal = _submit(session)
    row = request_for_assessment(session, request.aggregate_id)
    bus = build_command_bus(session, build_dispatcher())
    first = bus.dispatch(StartAssessment(
        command_id=uuid4(),
        request_id=request.aggregate_id,
        expected_version=row["version"],
        agent_run_id=uuid4(),
        model="fake",
    ))
    assert first.version == row["version"] + 1
    with pytest.raises(ConcurrencyError):
        bus.dispatch(StartAssessment(
            command_id=uuid4(),
            request_id=request.aggregate_id,
            expected_version=row["version"],
            agent_run_id=uuid4(),
            model="fake",
        ))
    stored = session.execute(sa.select(rm_requests.c.status)).scalar_one()
    assert stored == "AI_PROCESSING"
    events = EventStoreRepository(session, build_dispatcher()).load(request.aggregate_id, "InvestmentRequest")
    assert sum(event.event_type == "AssessmentStarted" for event in events) == 1


def test_infrastructure_failure_aborts_without_a_final_failure(session):
    _repo, request, investor_id, goal = _submit(session)
    row = request_for_assessment(session, request.aggregate_id)

    def down(_prompt):
        raise InfrastructureError("Ollama", "connection refused")

    services, calls, _catalog = _services(mode="deep", deep=down)
    status, _outcome = process_request(session, row, services, now=NOW)
    assert status == "aborted"
    assert calls["synth"] == 0
    events = EventStoreRepository(session, build_dispatcher()).load(request.aggregate_id, "InvestmentRequest")
    assert [event.event_type for event in events][-1] == "AssessmentAborted"
    assert events[-1].payload["attempt_not_counted"] is True
    assert not any(event.event_type == "AIAssessmentFailed" for event in events)
    assert session.execute(sa.select(rm_requests.c.status)).scalar_one() == "SUBMITTED"
    loaded = InvestmentRequest.from_events(events)
    assert loaded.content_failures == 0
    assert loaded.status is RequestStatus.SUBMITTED
    viewed = get_goal(session, goal.aggregate_id, investor_id)
    assert viewed["requestStatus"] == "SUBMITTED"
    assert viewed["assessment"] is None
    ok = {"status": "ok", "detail": "x"}
    with patch("app.controllers.health.check_database", return_value=ok), \
         patch("app.controllers.health.check_ollama", return_value=ok), \
         patch("app.controllers.health.check_chroma", return_value=ok):
        response = create_app(QuietConfig).test_client().get("/api/health")
    assert response.status_code == 200


def test_third_content_failure_is_terminal_and_retry_waits(session):
    _repo, request, _investor, _goal = _submit(session)
    services, _calls, _catalog = _services(products=[])
    for _ in range(3):
        row = request_for_assessment(session, request.aggregate_id)
        status, _outcome = process_request(session, row, services, now=NOW)
        assert status == "failed"
    assert session.execute(sa.select(rm_requests.c.status)).scalar_one() == "FAILED"
    with pytest.raises(BusinessRuleViolation) as exc:
        loaded = InvestmentRequest.from_events(
            EventStoreRepository(session, build_dispatcher()).load(request.aggregate_id, "InvestmentRequest")
        )
        loaded.start_assessment(agent_run_id=uuid4(), model="fake")
    assert exc.value.code == "ASSESSMENT_EXHAUSTED"


def test_failed_attempt_is_not_polled_before_retry(session):
    _repo, request, _investor, _goal = _submit(session)
    services, _calls, _catalog = _services(products=[])
    row = request_for_assessment(session, request.aggregate_id)
    process_request(session, row, services, now=NOW)
    assert pending_requests(session, NOW) == []
    assert len(pending_requests(session, NOW + timedelta(minutes=11))) == 1


def test_stuck_processing_returns_to_the_queue(session):
    _repo, request, _investor, _goal = _submit(session)
    row = request_for_assessment(session, request.aggregate_id)
    bus = build_command_bus(session, build_dispatcher())
    bus.dispatch(StartAssessment(
        command_id=uuid4(),
        request_id=request.aggregate_id,
        expected_version=row["version"],
        agent_run_id=uuid4(),
        model="fake",
    ))
    later = datetime.now(UTC) + timedelta(minutes=11)
    assert stuck_requests(session, later)
    services, _calls, _catalog = _services()
    outcomes = process_batch(session, lambda _snapshot: services, now=later)
    assert "released" in outcomes
    assert session.execute(sa.select(rm_requests.c.status)).scalar_one() == "SUBMITTED"
    texts = session.execute(sa.select(rm_request_timeline.c.display_text)).scalars().all()
    assert "ההערכה האוטומטית התחילה" in texts
    assert "ההערכה לא הושלמה ותחזור לתור" in texts


def test_completed_assessment_is_projected_for_the_goal(session):
    _repo, request, investor_id, goal = _submit(session)
    services, _calls, _catalog = _services()
    row = request_for_assessment(session, request.aggregate_id)
    status, outcome = process_request(session, row, services, now=NOW)
    assert status == "completed"
    stored = session.execute(sa.select(rm_requests.c.status, rm_requests.c.overall_score)).one()
    assert stored.status == "AI_EVALUATED"
    assert stored.overall_score == outcome.payload["overall_score"]
    assert session.execute(sa.select(sa.func.count()).select_from(rm_assessments)).scalar_one() == 1
    viewed = get_goal(session, goal.aggregate_id, investor_id)
    assert viewed["assessment"]["overallScore"] == outcome.payload["overall_score"]
    assert viewed["assessment"]["pendingReview"] is True
    assert viewed["assessment"]["channelScores"]["hishtalmut"] <= 40


def test_candidate_query_keeps_active_products_in_allowed_channels(session):
    active = uuid4()
    inactive = uuid4()
    moment = datetime(2026, 10, 14)
    for product_id, active_flag, product_type in (
        (active, True, "GEMEL_INVESTMENT"),
        (inactive, False, "GEMEL_INVESTMENT"),
        (uuid4(), True, "STOCK"),
    ):
        session.execute(sa.insert(rm_products).values(
            product_id=product_id,
            type=product_type,
            name="מסלול",
            institution_id=uuid4(),
            institution_name="גוף",
            track="כללי",
            symbol=None,
            fee_deposit=Decimal(0),
            fee_assets=Decimal("0.60"),
            return_1y=Decimal(1),
            return_3y=Decimal(1),
            return_5y=Decimal(1),
            std_dev=Decimal(1),
            risk_level=4,
            liquidity="HIGH",
            liquidity_terms="נזיל",
            tax_notes="מס",
            min_deposit=Decimal(0),
            description="תיאור",
            is_active=active_flag,
            search_text="מסלול",
            updated_at=moment,
        ))
    session.commit()
    found = find_candidate_products(
        session,
        risk_score=3,
        excluded_channels=["CAPITAL_MARKET"],
        liquidity_need="HIGH",
    )
    ids = {item["product_id"] for item in found}
    assert str(active) in ids
    assert str(inactive) not in ids
    assert all(item["channel"] != "capital_market" for item in found)
