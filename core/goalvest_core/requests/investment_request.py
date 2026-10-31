"""InvestmentRequest – הגשה, ביטול, הערכת AI, ליד והצעה. ראו docs/03 §3.9 ו-docs/08 §8.7."""

# InvestmentRequest is the request state machine (9 statuses, see RequestStatus).
# Every command method (submit, cancel, claim, send_offer, ...) first checks that the transition
# is legal for the current status - otherwise BusinessRuleViolation (HTTP 422 with a code) - and
# then records exactly one event via _record. Business rules live here, never in controllers
# or handlers. A FAILED request can be cancelled; saving the goal again resubmits it.

from dataclasses import dataclass
from enum import StrEnum
from uuid import UUID

from goalvest_core.aggregate import AggregateRoot
from goalvest_core.errors import BusinessRuleViolation
from goalvest_core.event import Event
from goalvest_core.events.investment_request import (
    AIAssessmentCompleted,
    AIAssessmentFailed,
    AssessmentAborted,
    AssessmentApproved,
    AssessmentRejected,
    AssessmentStarted,
    LeadClaimed,
    OfferAccepted,
    OfferDeclined,
    OfferSent,
    ReevaluationRequested,
)


class RequestStatus(StrEnum):
    SUBMITTED = "SUBMITTED"
    AI_PROCESSING = "AI_PROCESSING"
    AI_EVALUATED = "AI_EVALUATED"
    IN_REVIEW = "IN_REVIEW"
    REEVALUATION_REQUESTED = "REEVALUATION_REQUESTED"
    OFFER_SENT = "OFFER_SENT"
    ACCEPTED = "ACCEPTED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


@dataclass(frozen=True)
class OfferProduct:
    product_id: UUID
    institution_id: UUID
    active: bool


_QUEUEABLE = frozenset({RequestStatus.SUBMITTED, RequestStatus.REEVALUATION_REQUESTED})


CANCELLABLE_STATUSES = frozenset({
    RequestStatus.SUBMITTED,
    RequestStatus.AI_EVALUATED,
    RequestStatus.IN_REVIEW,
    # בקשה שנכשלה שלוש פעמים: המשקיע יכול לבטל אותה ולהגיש מחדש (עריכת יעד)
    RequestStatus.FAILED,
})

MAX_ASSESSMENT_ATTEMPTS = 3

# אירוע עתידי יכול להירשם כאן בלי ערך חדש ב-enum. אירועי הסוכן מטופלים במפורש.
STATUS_TRANSITIONS: dict[str, RequestStatus] = {}


class InvestmentRequest(AggregateRoot):
    aggregate_type = "InvestmentRequest"

    def __init__(self, aggregate_id: UUID | None = None) -> None:
        super().__init__(aggregate_id)
        self.status: RequestStatus | None = None
        self.goal_id: UUID | None = None
        self.investor_id: UUID | None = None
        self.consent_share_contact = False
        self.snapshot: dict = {}
        self.content_failures = 0
        self.completed_attempts = 0
        self.processing_attempt: int | None = None
        self.claimed_by: UUID | None = None
        self.claimed_institution: UUID | None = None
        self.assessment_review: str | None = None
        self.open_offer_id: UUID | None = None

    def submit(
        self,
        *,
        goal_id: UUID,
        investor_id: UUID,
        snapshot: dict,
        consent_share_contact: bool,
        metadata: dict | None = None,
    ) -> None:
        if self.version != 0:
            raise BusinessRuleViolation("הבקשה כבר הוגשה", code="ALREADY_SUBMITTED")
        risk = snapshot.get("risk") if isinstance(snapshot, dict) else None
        score = risk.get("score") if isinstance(risk, dict) else None
        if score is None:
            raise BusinessRuleViolation(
                "יש להשלים שאלון סיכון לפני הגשת בקשה",
                code="RISK_PROFILE_REQUIRED",
            )
        if consent_share_contact is not True:
            raise BusinessRuleViolation("יש לאשר שיתוף פרטים עם סוכנים", code="CONSENT_REQUIRED")
        self._record(
            "InvestmentRequestSubmitted",
            {
                "goal_id": str(goal_id),
                "investor_id": str(investor_id),
                "snapshot": snapshot,
                "consent_share_contact": True,
            },
            metadata,
        )

    def use_projected_status(self, status: RequestStatus | str) -> None:
        """המצב ב-rm_requests, כולל סטטוס שהסוכן יקבע לפני שהאירוע שלו נטען."""
        try:
            self.status = status if isinstance(status, RequestStatus) else RequestStatus(status)
        except ValueError as exc:
            raise BusinessRuleViolation("סטטוס הבקשה אינו מוכר", code="CANCEL_NOT_ALLOWED") from exc

    def ensure_goal_change_allowed(self) -> None:
        if self.status is RequestStatus.AI_PROCESSING:
            raise BusinessRuleViolation(
                "אי אפשר לערוך או לארכב יעד בזמן שהבקשה בעיבוד",
                code="REQUEST_IN_PROCESSING",
            )

    def cancel(self, *, by: str, reason: str = "", metadata: dict | None = None) -> None:
        if self.status is RequestStatus.AI_PROCESSING:
            raise BusinessRuleViolation(
                "אי אפשר לבטל בקשה בזמן עיבוד",
                code="REQUEST_IN_PROCESSING",
            )
        if self.status not in CANCELLABLE_STATUSES:
            raise BusinessRuleViolation("אי אפשר לבטל בקשה בסטטוס הזה", code="CANCEL_NOT_ALLOWED")
        cleaned = reason.strip()
        if len(cleaned) > 500:
            raise BusinessRuleViolation(
                "הסיבה ארוכה מדי",
                code="INVALID_REASON",
                fields={"reason": "עד 500 תווים"},
            )
        self._record("RequestCancelled", {"by": by, "reason": cleaned}, metadata)

    def start_assessment(self, *, agent_run_id: UUID, model: str, metadata: dict | None = None) -> None:
        self._ensure_submittable()
        started = AssessmentStarted(
            attempt=self._next_attempt(),
            agent_run_id=str(agent_run_id),
            model=model,
        )
        self._record(started.event_type, started.payload(), metadata)

    def claim(self, *, agent_id: UUID, institution_id: UUID, metadata: dict | None = None) -> None:
        if self.status is not RequestStatus.AI_EVALUATED:
            raise BusinessRuleViolation("אפשר לקחת רק ליד אחרי הערכת AI", code="CLAIM_NOT_ALLOWED")
        claimed = LeadClaimed(agent_id=str(agent_id), institution_id=str(institution_id))
        self._record(claimed.event_type, claimed.payload(), metadata)

    def approve_assessment(self, *, agent_id: UUID, note: str = "", metadata: dict | None = None) -> None:
        self._ensure_reviewer(agent_id)
        cleaned = _bounded(note, "note", "INVALID_NOTE", required=False)
        approved = AssessmentApproved(agent_id=str(agent_id), note=cleaned or None)
        self._record(approved.event_type, approved.payload(), metadata)

    def reject_assessment(self, *, agent_id: UUID, note: str, metadata: dict | None = None) -> None:
        self._ensure_reviewer(agent_id)
        cleaned = _bounded(note, "note", "INVALID_NOTE", required=True, empty="חובה לכתוב הערה בדחייה")
        rejected = AssessmentRejected(agent_id=str(agent_id), note=cleaned)
        self._record(rejected.event_type, rejected.payload(), metadata)

    def request_reevaluation(self, *, agent_id: UUID, reason: str, metadata: dict | None = None) -> None:
        self._ensure_reviewer(agent_id)
        cleaned = _bounded(reason, "reason", "INVALID_REASON", required=True, empty="חובה לכתוב סיבה")
        requested = ReevaluationRequested(agent_id=str(agent_id), reason=cleaned)
        self._record(requested.event_type, requested.payload(), metadata)

    def send_offer(
        self,
        *,
        agent_id: UUID,
        institution_id: UUID,
        offer_id: UUID,
        items: list[dict],
        message: str,
        products: tuple[OfferProduct, ...],
        metadata: dict | None = None,
    ) -> None:
        if self.status is not RequestStatus.IN_REVIEW or self.claimed_by != agent_id:
            raise BusinessRuleViolation("אפשר לשלוח הצעה רק אחרי לקיחת הליד", code="OFFER_NOT_ALLOWED")
        if self.claimed_institution != institution_id:
            raise BusinessRuleViolation("אפשר לשלוח הצעה רק אחרי לקיחת הליד", code="OFFER_NOT_ALLOWED")
        normalized = _offer_items(items, institution_id, products)
        cleaned = _bounded(message, "message", "INVALID_MESSAGE", required=True, empty="חובה לכתוב הודעה", limit=2000)
        sent = OfferSent(
            offer_id=str(offer_id),
            agent_id=str(agent_id),
            items=normalized,
            message=cleaned,
        )
        self._record(sent.event_type, sent.payload(), metadata)

    def accept_offer(self, *, offer_id: UUID, metadata: dict | None = None) -> None:
        self._ensure_open_offer(offer_id)
        accepted = OfferAccepted(offer_id=str(offer_id))
        self._record(accepted.event_type, accepted.payload(), metadata)

    def decline_offer(self, *, offer_id: UUID, reason: str = "", metadata: dict | None = None) -> None:
        self._ensure_open_offer(offer_id)
        cleaned = reason.strip()
        if len(cleaned) > 500:
            raise BusinessRuleViolation(
                "הסיבה ארוכה מדי",
                code="INVALID_REASON",
                fields={"reason": "עד 500 תווים"},
            )
        declined = OfferDeclined(offer_id=str(offer_id), reason=cleaned or None)
        self._record(declined.event_type, declined.payload(), metadata)

    def complete_assessment(self, assessment: dict, metadata: dict | None = None) -> None:
        if self.status is not RequestStatus.AI_PROCESSING:
            raise BusinessRuleViolation("אין הערכה בעיבוד", code="ASSESSMENT_NOT_PROCESSING")
        body = dict(assessment)
        body["attempt"] = self.processing_attempt or 1
        completed = AIAssessmentCompleted(body)
        self._record(completed.event_type, completed.payload(), metadata)

    def fail_assessment(
        self,
        *,
        error_code: str,
        message: str,
        retry_at: str,
        metadata: dict | None = None,
    ) -> None:
        if self.status is not RequestStatus.AI_PROCESSING:
            raise BusinessRuleViolation("אין הערכה בעיבוד", code="ASSESSMENT_NOT_PROCESSING")
        attempt = self.processing_attempt or (self.content_failures + 1)
        terminal = self.content_failures + 1 >= MAX_ASSESSMENT_ATTEMPTS
        failed = AIAssessmentFailed(
            attempt=attempt,
            error_code=error_code,
            message=message.strip()[:500],
            retry_at=None if terminal else retry_at,
        )
        self._record(failed.event_type, failed.payload(), metadata)

    def abort_assessment(self, *, reason: str, metadata: dict | None = None) -> None:
        if self.status is not RequestStatus.AI_PROCESSING:
            raise BusinessRuleViolation("אין הערכה בעיבוד", code="ASSESSMENT_NOT_PROCESSING")
        aborted = AssessmentAborted(reason=reason.strip()[:300])
        self._record(aborted.event_type, aborted.payload(), metadata)

    def _ensure_submittable(self) -> None:
        if self.content_failures >= MAX_ASSESSMENT_ATTEMPTS or self.status is RequestStatus.FAILED:
            raise BusinessRuleViolation("מוצו ניסיונות ההערכה", code="ASSESSMENT_EXHAUSTED")
        if self.status not in _QUEUEABLE:
            raise BusinessRuleViolation("אי אפשר להתחיל הערכה בסטטוס הזה", code="ASSESSMENT_NOT_ALLOWED")

    def _next_attempt(self) -> int:
        return max(self.content_failures, self.completed_attempts) + 1

    def _ensure_reviewer(self, agent_id: UUID) -> None:
        if self.status is not RequestStatus.IN_REVIEW or self.claimed_by != agent_id:
            raise BusinessRuleViolation(
                "רק הסוכן שלקח את הליד יכול לבצע את הפעולה",
                code="REVIEW_NOT_ALLOWED",
            )

    def _ensure_open_offer(self, offer_id: UUID) -> None:
        if self.status is not RequestStatus.OFFER_SENT or self.open_offer_id != offer_id:
            raise BusinessRuleViolation("אין הצעה פתוחה", code="OFFER_NOT_OPEN")

    def _when(self, event: Event) -> None:
        if event.event_type == "InvestmentRequestSubmitted":
            payload = event.payload
            self.goal_id = UUID(payload["goal_id"])
            self.investor_id = UUID(payload["investor_id"])
            self.snapshot = dict(payload["snapshot"])
            self.consent_share_contact = bool(payload["consent_share_contact"])
            self.status = RequestStatus.SUBMITTED
            return
        if event.event_type == "RequestCancelled":
            self.status = RequestStatus.CANCELLED
            return
        if event.event_type == "AssessmentStarted":
            self.status = RequestStatus.AI_PROCESSING
            raw = event.payload.get("attempt")
            self.processing_attempt = int(raw) if raw is not None else self.content_failures + 1
            return
        if event.event_type == "AIAssessmentCompleted":
            self.status = RequestStatus.AI_EVALUATED
            self.processing_attempt = None
            raw = event.payload.get("attempt")
            if raw is not None:
                self.completed_attempts = int(raw)
            self.claimed_by = None
            self.claimed_institution = None
            self.assessment_review = None
            self.open_offer_id = None
            return
        if event.event_type == "LeadClaimed":
            self.claimed_by = UUID(event.payload["agent_id"])
            self.claimed_institution = UUID(event.payload["institution_id"])
            self.status = RequestStatus.IN_REVIEW
            return
        if event.event_type == "AssessmentApproved":
            self.assessment_review = "approved"
            return
        if event.event_type == "AssessmentRejected":
            self.assessment_review = "rejected"
            return
        if event.event_type == "ReevaluationRequested":
            self.status = RequestStatus.REEVALUATION_REQUESTED
            self.claimed_by = None
            self.claimed_institution = None
            self.assessment_review = None
            return
        if event.event_type == "OfferSent":
            self.open_offer_id = UUID(event.payload["offer_id"])
            self.status = RequestStatus.OFFER_SENT
            return
        if event.event_type == "OfferAccepted":
            self.status = RequestStatus.ACCEPTED
            return
        if event.event_type == "OfferDeclined":
            self.open_offer_id = None
            self.status = RequestStatus.IN_REVIEW
            return
        if event.event_type == "AIAssessmentFailed":
            self.content_failures += 1
            self.processing_attempt = None
            self.status = (
                RequestStatus.FAILED
                if self.content_failures >= MAX_ASSESSMENT_ATTEMPTS
                else RequestStatus.SUBMITTED
            )
            return
        if event.event_type == "AssessmentAborted":
            self.status = RequestStatus.SUBMITTED
            self.processing_attempt = None
            return
        transition = STATUS_TRANSITIONS.get(event.event_type)
        if transition is not None:
            self.status = transition
            return
        raise NotImplementedError(f"InvestmentRequest אינו מטפל ב-{event.event_type}")


def _bounded(
    value: str,
    field: str,
    code: str,
    *,
    required: bool,
    empty: str = "",
    limit: int = 500,
) -> str:
    cleaned = value.strip()
    if required and not cleaned:
        raise BusinessRuleViolation(empty, code=code, fields={field: "חובה"})
    if len(cleaned) > limit:
        raise BusinessRuleViolation(
            "הטקסט ארוך מדי",
            code=code,
            fields={field: f"עד {limit} תווים"},
        )
    return cleaned


def _offer_items(items: list[dict], institution_id: UUID, products: tuple[OfferProduct, ...]) -> list[dict]:
    if not 1 <= len(items) <= 3:
        raise BusinessRuleViolation(
            "יש לבחור בין מוצר אחד לשלושה",
            code="INVALID_ITEMS",
            fields={"items": "1–3 מוצרים"},
        )
    catalog = {product.product_id: product for product in products}
    seen: set[UUID] = set()
    normalized: list[dict] = []
    total = 0
    for item in items:
        product_id = item["product_id"]
        percent = item["percent"]
        if not isinstance(percent, int) or isinstance(percent, bool) or percent < 1:
            raise BusinessRuleViolation(
                "אחוז ההקצאה אינו תקין",
                code="INVALID_ITEMS",
                fields={"percent": "מספר שלם חיובי"},
            )
        if product_id in seen:
            raise BusinessRuleViolation(
                "אי אפשר לבחור את אותו מוצר פעמיים",
                code="INVALID_ITEMS",
                fields={"items": "מוצרים שונים"},
            )
        seen.add(product_id)
        product = catalog.get(product_id)
        if product is None or not product.active or product.institution_id != institution_id:
            raise BusinessRuleViolation("המוצר אינו פעיל או אינו שייך לגוף", code="PRODUCT_NOT_ALLOWED")
        total += percent
        normalized.append({"product_id": str(product_id), "percent": percent})
    if total != 100:
        raise BusinessRuleViolation("סכום האחוזים חייב להיות 100", code="ALLOCATION_NOT_100")
    return normalized
