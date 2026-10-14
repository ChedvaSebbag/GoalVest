"""InvestorProfile: שאלון, ציון, ומילוי חוזר."""

from datetime import date
from uuid import uuid4

import pytest
from goalvest_core import BusinessRuleViolation
from goalvest_core.investor import InvestorProfile, evaluate

TODAY = date(2026, 10, 13)


def _answers(**overrides):
    raw = {
        "birth_year": 1994,
        "horizon": "Y6_TO_10",
        "drop_reaction": "WAIT",
        "experience": "FUNDS",
        "income_stability": "SALARIED",
        "emergency_fund": "YES",
        "marital_status": "MARRIED",
        "monthly_income_range": "FROM_20K_TO_35K",
        "existing_products": ["HISHTALMUT"],
    }
    raw.update(overrides)
    return raw


def test_given_no_profile_when_assessment_then_created_and_scored():
    profile = InvestorProfile(uuid4())
    profile.record_assessment(_answers(), today=TODAY)
    events = profile.uncommitted_events
    assert [event.event_type for event in events] == ["InvestorProfileCreated", "RiskProfileAssessed"]
    assert profile.risk_score == 4
    assert profile.risk_label == "מאוזן-צמיחה"
    assert profile.birth_year == 1994
    assert profile.has_emergency_fund is True


def test_score_rounds_half_up_and_covers_both_ends():
    low = evaluate(_answers(
        birth_year=1960,
        horizon="UNDER_3",
        drop_reaction="SELL_ALL",
        experience="NONE",
        income_stability="UNSTABLE",
        emergency_fund="NONE",
    ), TODAY)
    high = evaluate(_answers(
        birth_year=2000,
        horizon="OVER_20",
        drop_reaction="BUY_MORE",
        experience="ACTIVE",
        income_stability="SURPLUS",
        emergency_fund="YES",
    ), TODAY)
    half = evaluate(_answers(
        birth_year=1970,
        horizon="UNDER_3",
        drop_reaction="SELL_ALL",
        experience="NONE",
        income_stability="UNSTABLE",
        emergency_fund="YES",
    ), TODAY)
    assert (low.score, low.label) == (1, "סולידי")
    assert (high.score, high.label) == (5, "צמיחה")
    # גיל 56 → 2, וחמש תשובות של 1, וקרן חירום 5: (2+1+1+1+1+5)/6 = 1.833 → 2
    assert half.score == 2


def test_given_assessed_profile_when_retaken_then_only_new_assessment():
    user_id = uuid4()
    first = InvestorProfile(user_id)
    first.record_assessment(_answers(), today=TODAY)
    again = InvestorProfile.from_events(first.uncommitted_events)
    again.record_assessment(_answers(emergency_fund="NONE", horizon="UNDER_3"), today=TODAY)
    assert [event.event_type for event in again.uncommitted_events] == ["RiskProfileAssessed"]
    assert again.risk_score == 3
    assert again.has_emergency_fund is False


def test_invalid_answer_records_nothing():
    profile = InvestorProfile(uuid4())
    with pytest.raises(BusinessRuleViolation) as caught:
        profile.record_assessment(_answers(horizon="SOON"), today=TODAY)
    assert caught.value.code == "INVALID_ANSWERS"
    assert "horizon" in caught.value.fields
    assert profile.uncommitted_events == ()


def test_second_profile_create_records_nothing():
    profile = InvestorProfile(uuid4())
    profile.record_assessment(_answers(), today=TODAY)
    saved = InvestorProfile.from_events(profile.uncommitted_events)
    with pytest.raises(BusinessRuleViolation) as caught:
        saved.create_profile(
            birth_year=1990,
            marital_status="SINGLE",
            monthly_income_range="UP_TO_10K",
            has_emergency_fund=False,
            existing_products=["NONE"],
            today=TODAY,
        )
    assert caught.value.code == "PROFILE_EXISTS"
    assert saved.uncommitted_events == ()
