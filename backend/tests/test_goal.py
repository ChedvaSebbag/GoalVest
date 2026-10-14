"""Goal: ולידציות FR-12, עדכון וארכוב."""

from datetime import date, timedelta
from decimal import Decimal
from uuid import uuid4

import pytest
from goalvest_core import BusinessRuleViolation
from goalvest_core.goals import Goal
from goalvest_core.goals.dates import add_months

TODAY = date(2026, 10, 13)
INVESTOR = uuid4()


def _fields(**overrides):
    data = {
        "goal_type": "APARTMENT",
        "title": "דירה",
        "initial_amount": Decimal("150000.00"),
        "monthly_deposit": Decimal("3000.00"),
        "target_amount": Decimal("400000.00"),
        "target_date": add_months(TODAY, 24),
        "flexibility": "YEAR_1",
        "liquidity_need": "PARTIAL",
        "excluded_channels": [],
        "preferred_channels": ["GEMEL_POLICY"],
        "preferred_institutions": [],
    }
    data.update(overrides)
    return data


def _goal() -> Goal:
    goal = Goal()
    goal.create(investor_id=INVESTOR, today=TODAY, known_institutions=set(), **_fields())
    return goal


def test_given_valid_input_when_create_then_goal_created():
    goal = _goal()
    event = goal.uncommitted_events[0]
    assert event.event_type == "GoalCreated"
    assert event.payload["type"] == "APARTMENT"
    assert event.payload["preferred_channels"] == ["GEMEL_POLICY"]
    assert goal.status == "ACTIVE"
    assert goal.investor_id == INVESTOR


def test_zero_initial_with_monthly_deposit_is_valid():
    goal = Goal()
    goal.create(
        investor_id=INVESTOR,
        today=TODAY,
        known_institutions=set(),
        **_fields(initial_amount=Decimal(0)),
    )
    assert goal.initial_amount == Decimal("0.00")
    assert goal.uncommitted_events[0].event_type == "GoalCreated"


@pytest.mark.parametrize(
    ("overrides", "code", "field"),
    [
        ({"initial_amount": Decimal(0), "monthly_deposit": Decimal(0)}, "INVALID_AMOUNTS", "initialAmount"),
        ({"target_amount": Decimal(0)}, "INVALID_TARGET_AMOUNT", "targetAmount"),
        ({"initial_amount": Decimal(-1)}, "INVALID_INITIAL_AMOUNT", "initialAmount"),
        ({"target_date": TODAY}, "INVALID_TARGET_DATE", "targetDate"),
        ({"target_date": add_months(TODAY, 6) - timedelta(days=1)}, "INVALID_TARGET_DATE", "targetDate"),
    ],
)
def test_invalid_goal_records_nothing(overrides, code, field):
    goal = Goal()
    with pytest.raises(BusinessRuleViolation) as caught:
        goal.create(investor_id=INVESTOR, today=TODAY, known_institutions=set(), **_fields(**overrides))
    assert caught.value.code == code
    assert field in caught.value.fields
    assert goal.uncommitted_events == ()


def test_exact_six_months_is_valid():
    goal = Goal()
    goal.create(
        investor_id=INVESTOR,
        today=TODAY,
        known_institutions=set(),
        **_fields(target_date=add_months(TODAY, 6)),
    )
    assert goal.target_date == add_months(TODAY, 6)


def test_update_records_only_changed_fields_and_archive_is_once():
    created = _goal().uncommitted_events
    goal = Goal.from_events(created)
    goal.update(today=TODAY, known_institutions=set(), **_fields(title="דירה ראשונה"))
    updated = goal.uncommitted_events
    assert len(updated) == 1
    assert updated[0].event_type == "GoalUpdated"
    assert updated[0].payload == {"title": "דירה ראשונה"}

    archived = Goal.from_events([*created, *updated])
    archived.archive("לא רלוונטי")
    assert archived.status == "ARCHIVED"
    with pytest.raises(BusinessRuleViolation) as caught:
        archived.update(today=TODAY, known_institutions=set(), **_fields())
    assert caught.value.code == "GOAL_ARCHIVED"


def test_second_active_request_is_rejected():
    goal = Goal.from_events(_goal().uncommitted_events)
    goal.ensure_no_active_request(None)
    with pytest.raises(BusinessRuleViolation) as caught:
        goal.ensure_no_active_request(uuid4())
    assert caught.value.code == "ACTIVE_REQUEST_EXISTS"
