"""אירועי הערכת AI על InvestmentRequest. ראו docs/07 §7.3 ו-docs/03 §3.9."""

from dataclasses import dataclass


@dataclass(frozen=True)
class AssessmentStarted:
    attempt: int
    agent_run_id: str
    model: str
    event_type: str = "AssessmentStarted"
    schema_version: int = 1

    def payload(self) -> dict:
        return {
            "attempt": self.attempt,
            "agent_run_id": self.agent_run_id,
            "model": self.model,
        }


@dataclass(frozen=True)
class AIAssessmentCompleted:
    assessment: dict
    event_type: str = "AIAssessmentCompleted"
    schema_version: int = 1

    def payload(self) -> dict:
        return dict(self.assessment)


@dataclass(frozen=True)
class AIAssessmentFailed:
    attempt: int
    error_code: str
    message: str
    retry_at: str | None
    event_type: str = "AIAssessmentFailed"
    schema_version: int = 1

    def payload(self) -> dict:
        return {
            "attempt": self.attempt,
            "error_code": self.error_code,
            "message": self.message,
            "retry_at": self.retry_at,
        }


@dataclass(frozen=True)
class LeadClaimed:
    agent_id: str
    institution_id: str
    event_type: str = "LeadClaimed"
    schema_version: int = 1

    def payload(self) -> dict:
        return {"agent_id": self.agent_id, "institution_id": self.institution_id}


@dataclass(frozen=True)
class AssessmentApproved:
    agent_id: str
    note: str | None = None
    event_type: str = "AssessmentApproved"
    schema_version: int = 1

    def payload(self) -> dict:
        body = {"agent_id": self.agent_id}
        if self.note:
            body["note"] = self.note
        return body


@dataclass(frozen=True)
class AssessmentRejected:
    agent_id: str
    note: str
    event_type: str = "AssessmentRejected"
    schema_version: int = 1

    def payload(self) -> dict:
        return {"agent_id": self.agent_id, "note": self.note}


@dataclass(frozen=True)
class ReevaluationRequested:
    agent_id: str
    reason: str
    event_type: str = "ReevaluationRequested"
    schema_version: int = 1

    def payload(self) -> dict:
        return {"agent_id": self.agent_id, "reason": self.reason}


@dataclass(frozen=True)
class OfferSent:
    offer_id: str
    agent_id: str
    items: list
    message: str
    event_type: str = "OfferSent"
    schema_version: int = 1

    def payload(self) -> dict:
        return {
            "offer_id": self.offer_id,
            "agent_id": self.agent_id,
            "items": list(self.items),
            "message": self.message,
        }


@dataclass(frozen=True)
class OfferAccepted:
    offer_id: str
    event_type: str = "OfferAccepted"
    schema_version: int = 1

    def payload(self) -> dict:
        return {"offer_id": self.offer_id}


@dataclass(frozen=True)
class OfferDeclined:
    offer_id: str
    reason: str | None = None
    event_type: str = "OfferDeclined"
    schema_version: int = 1

    def payload(self) -> dict:
        body = {"offer_id": self.offer_id}
        if self.reason:
            body["reason"] = self.reason
        return body


@dataclass(frozen=True)
class AssessmentAborted:
    reason: str
    attempt_not_counted: bool = True
    event_type: str = "AssessmentAborted"
    schema_version: int = 1

    def payload(self) -> dict:
        return {"reason": self.reason, "attempt_not_counted": True}
