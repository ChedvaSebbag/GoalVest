"""אירוע → שורה ב-rm_*. כולל ציר זמן ובקשה פעילה."""

from datetime import date
from decimal import Decimal
from uuid import uuid4

import sqlalchemy as sa
from app.bootstrap import build_dispatcher
from app.infrastructure.event_store import EventStoreRepository
from app.infrastructure.tables import rm_goals, rm_investor_profiles, rm_request_timeline, rm_requests
from goalvest_core.accounts import UserAccount
from goalvest_core.goals import Goal
from goalvest_core.goals.dates import add_months
from goalvest_core.investor import InvestorProfile
from goalvest_core.requests import InvestmentRequest

TODAY = date(2026, 10, 13)


def _repo(session) -> EventStoreRepository:
    return EventStoreRepository(session, build_dispatcher())


def test_user_and_profile_can_share_user_id_at_version_1(session):
    user_id = uuid4()
    account = UserAccount(user_id)
    account.register(
        email="noa@mail.com",
        full_name="נועה לוי",
        phone="0501234567",
        password="Secret12",
        role="INVESTOR",
        hash_password=lambda value: f"hashed:{value}",
    )
    profile = InvestorProfile(user_id)
    profile.record_assessment({
        "birth_year": 1994,
        "horizon": "Y6_TO_10",
        "drop_reaction": "WAIT",
        "experience": "FUNDS",
        "income_stability": "SALARIED",
        "emergency_fund": "YES",
        "marital_status": "MARRIED",
        "monthly_income_range": "FROM_20K_TO_35K",
        "existing_products": ["HISHTALMUT"],
    }, today=TODAY)
    repo = _repo(session)
    repo.append(user_id, 0, account.uncommitted_events)
    repo.append(user_id, 0, profile.uncommitted_events)
    session.commit()
    row = session.execute(sa.select(rm_investor_profiles)).mappings().one()
    assert row["user_id"] == user_id
    assert row["risk_score"] == 4
    assert row["risk_label"] == "מאוזן-צמיחה"
    assert len(repo.load(user_id, "UserAccount")) == 1
    assert len(repo.load(user_id, "InvestorProfile")) == 2


def test_goal_request_and_cancel_update_read_models(session):
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
        target_date=add_months(TODAY, 24),
        flexibility="YEAR_1",
        liquidity_need="PARTIAL",
        excluded_channels=[],
        preferred_channels=["GEMEL_POLICY"],
        preferred_institutions=[],
    )
    request = InvestmentRequest()
    request.submit(
        goal_id=goal.aggregate_id,
        investor_id=investor_id,
        snapshot={"goal": {"title": "דירה"}, "risk": {"score": 4, "label": "מאוזן-צמיחה", "answers": {}}},
        consent_share_contact=True,
    )
    repo = _repo(session)
    repo.append(goal.aggregate_id, 0, goal.uncommitted_events)
    repo.append(request.aggregate_id, 0, request.uncommitted_events)
    session.commit()

    stored = session.execute(sa.select(rm_goals)).mappings().one()
    assert stored["active_request_id"] == request.aggregate_id
    assert stored["title"] == "דירה"
    assert session.execute(sa.select(rm_requests.c.status)).scalar_one() == "SUBMITTED"
    assert session.execute(sa.select(sa.func.count()).select_from(rm_request_timeline)).scalar_one() == 1

    loaded = InvestmentRequest.from_events(repo.load(request.aggregate_id, "InvestmentRequest"))
    loaded.cancel(by=str(investor_id), reason="GOAL_UPDATED")
    repo.append(request.aggregate_id, 1, loaded.uncommitted_events)
    session.commit()
    assert session.execute(sa.select(rm_requests.c.status)).scalar_one() == "CANCELLED"
    assert session.execute(sa.select(rm_goals.c.active_request_id)).scalar_one() is None
    texts = session.execute(
        sa.select(rm_request_timeline.c.display_text).order_by(rm_request_timeline.c.global_position)
    ).scalars().all()
    assert texts == ["הבקשה הוגשה", "הבקשה נסגרה בעקבות עדכון היעד"]
