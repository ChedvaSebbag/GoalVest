"""InvestmentRequest: הגשה, ביטול משלושת הסטטוסים, וחסימה בזמן עיבוד."""

from uuid import uuid4

import pytest
from goalvest_core import BusinessRuleViolation, Event
from goalvest_core.requests import STATUS_TRANSITIONS, InvestmentRequest, RequestStatus


def _snapshot(score=3):
    return {"goal": {"title": "דירה"}, "risk": {"score": score, "label": "מאוזן", "answers": {}}}


def _submitted() -> InvestmentRequest:
    request = InvestmentRequest()
    request.submit(
        goal_id=uuid4(),
        investor_id=uuid4(),
        snapshot=_snapshot(),
        consent_share_contact=True,
    )
    return request


def test_submit_without_risk_score_or_consent_records_nothing():
    bare = InvestmentRequest()
    with pytest.raises(BusinessRuleViolation) as missing:
        bare.submit(goal_id=uuid4(), investor_id=uuid4(), snapshot=_snapshot(None), consent_share_contact=True)
    assert missing.value.code == "RISK_PROFILE_REQUIRED"
    assert bare.uncommitted_events == ()

    with pytest.raises(BusinessRuleViolation) as consent:
        bare.submit(goal_id=uuid4(), investor_id=uuid4(), snapshot=_snapshot(), consent_share_contact=False)
    assert consent.value.code == "CONSENT_REQUIRED"


@pytest.mark.parametrize("status", [RequestStatus.SUBMITTED, RequestStatus.AI_EVALUATED, RequestStatus.IN_REVIEW])
def test_cancel_is_allowed_from_submitted_evaluated_and_review(status):
    request = _submitted()
    request.use_projected_status(status)
    request.cancel(by="investor", reason="התחרטתי")
    cancelled = request.uncommitted_events[-1]
    assert cancelled.event_type == "RequestCancelled"
    assert cancelled.payload == {"by": "investor", "reason": "התחרטתי"}
    assert request.status is RequestStatus.CANCELLED


def test_processing_blocks_cancel_and_goal_change():
    request = _submitted()
    request.use_projected_status(RequestStatus.AI_PROCESSING)
    with pytest.raises(BusinessRuleViolation) as cancel:
        request.cancel(by="investor")
    assert cancel.value.code == "REQUEST_IN_PROCESSING"
    with pytest.raises(BusinessRuleViolation) as edit:
        request.ensure_goal_change_allowed()
    assert edit.value.code == "REQUEST_IN_PROCESSING"
    assert request.uncommitted_events[-1].event_type == "InvestmentRequestSubmitted"


def test_status_hook_accepts_a_future_agent_event_without_a_new_enum_value():
    request = InvestmentRequest.from_events(_submitted().uncommitted_events)
    STATUS_TRANSITIONS["AssessmentStarted"] = RequestStatus.AI_PROCESSING
    try:
        request.apply(Event(
            event_id=uuid4(),
            aggregate_id=request.aggregate_id,
            version=2,
            event_type="AssessmentStarted",
            aggregate_type="InvestmentRequest",
            payload={},
        ))
    finally:
        STATUS_TRANSITIONS.pop("AssessmentStarted", None)
    assert request.status is RequestStatus.AI_PROCESSING
    assert request.uncommitted_events == ()
