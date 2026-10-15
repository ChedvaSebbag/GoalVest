"""InvestmentRequest: הגשה, ביטול משלושת הסטטוסים, וחסימה בזמן עיבוד."""

from uuid import UUID, uuid4

import pytest
from goalvest_core import BusinessRuleViolation, Event
from goalvest_core.requests import STATUS_TRANSITIONS, InvestmentRequest, RequestStatus
from goalvest_core.requests.investment_request import OfferProduct


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


def _evaluated() -> tuple[InvestmentRequest, UUID, UUID]:
    request = _submitted()
    request.start_assessment(agent_run_id=uuid4(), model="fake")
    request.complete_assessment({"overall_score": 70, "rationale": "נימוק"})
    return request, uuid4(), uuid4()


def _claimed():
    request, agent_id, institution_id = _evaluated()
    request.claim(agent_id=agent_id, institution_id=institution_id)
    return request, agent_id, institution_id


def test_approve_does_not_change_status_and_reject_requires_a_note():
    request, agent_id, _institution = _claimed()
    request.approve_assessment(agent_id=agent_id, note="נראה סביר")
    assert request.status is RequestStatus.IN_REVIEW
    assert request.assessment_review == "approved"
    with pytest.raises(BusinessRuleViolation) as caught:
        request.reject_assessment(agent_id=agent_id, note=" ")
    assert caught.value.code == "INVALID_NOTE"
    assert request.uncommitted_events[-1].event_type == "AssessmentApproved"


def test_offer_allocation_must_sum_to_100_and_accept_closes_the_request():
    request, agent_id, institution_id = _claimed()
    product_id = uuid4()
    products = (OfferProduct(product_id=product_id, institution_id=institution_id, active=True),)
    with pytest.raises(BusinessRuleViolation) as caught:
        request.send_offer(
            agent_id=agent_id,
            institution_id=institution_id,
            offer_id=uuid4(),
            items=[{"product_id": product_id, "percent": 90}],
            message="הצעה",
            products=products,
        )
    assert caught.value.code == "ALLOCATION_NOT_100"
    offer_id = uuid4()
    request.send_offer(
        agent_id=agent_id,
        institution_id=institution_id,
        offer_id=offer_id,
        items=[{"product_id": product_id, "percent": 100}],
        message="הצעה",
        products=products,
    )
    assert request.status is RequestStatus.OFFER_SENT
    request.decline_offer(offer_id=offer_id, reason="לא עכשיו")
    assert request.status is RequestStatus.IN_REVIEW
    second = uuid4()
    request.send_offer(
        agent_id=agent_id,
        institution_id=institution_id,
        offer_id=second,
        items=[{"product_id": product_id, "percent": 100}],
        message="הצעה שנייה",
        products=products,
    )
    request.accept_offer(offer_id=second)
    assert request.status is RequestStatus.ACCEPTED


def test_reevaluation_returns_the_request_to_the_agent_queue():
    request, agent_id, _institution = _claimed()
    request.request_reevaluation(agent_id=agent_id, reason="חסר מסלול")
    assert request.status is RequestStatus.REEVALUATION_REQUESTED
    request.start_assessment(agent_run_id=uuid4(), model="fake")
    assert request.status is RequestStatus.AI_PROCESSING
    assert request.uncommitted_events[-1].payload["attempt"] == 2


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
