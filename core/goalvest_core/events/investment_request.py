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
class AssessmentAborted:
    reason: str
    attempt_not_counted: bool = True
    event_type: str = "AssessmentAborted"
    schema_version: int = 1

    def payload(self) -> dict:
        return {"reason": self.reason, "attempt_not_counted": True}
