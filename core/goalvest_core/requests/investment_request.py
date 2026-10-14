"""InvestmentRequest – הגשה וביטול. סטטוסי הסוכן קיימים כאן לפני האירועים שמובילים אליהם."""

from enum import StrEnum
from uuid import UUID

from goalvest_core.aggregate import AggregateRoot
from goalvest_core.errors import BusinessRuleViolation
from goalvest_core.event import Event


class RequestStatus(StrEnum):
    SUBMITTED = "SUBMITTED"
    AI_PROCESSING = "AI_PROCESSING"
    AI_EVALUATED = "AI_EVALUATED"
    IN_REVIEW = "IN_REVIEW"
    CANCELLED = "CANCELLED"


CANCELLABLE_STATUSES = frozenset({
    RequestStatus.SUBMITTED,
    RequestStatus.AI_EVALUATED,
    RequestStatus.IN_REVIEW,
})

# הסוכן רושם כאן אירוע → סטטוס, בלי להוסיף ערך ל-enum ובלי אירוע מובנה חדש.
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
        transition = STATUS_TRANSITIONS.get(event.event_type)
        if transition is not None:
            self.status = transition
            return
        raise NotImplementedError(f"InvestmentRequest אינו מטפל ב-{event.event_type}")
