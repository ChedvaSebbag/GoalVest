"""נעילה, הערכה ושחרור. כל שינוי מצב נכתב כאירוע."""

import logging
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from app.bootstrap import build_command_bus, build_dispatcher
from app.commands.assessments import (
    AbortAssessment,
    CompleteAssessment,
    FailAssessment,
    StartAssessment,
)
from app.queries.assessments import QUEUED_STATUSES, pending_requests, request_for_assessment, stuck_requests
from goalvest_core import BusinessRuleViolation, ConcurrencyError
from sqlalchemy.orm import Session

from agent.errors import InfrastructureError
from agent.pipeline import Outcome, Services, run_assessment

logger = logging.getLogger(__name__)
_RETRY = timedelta(minutes=10)


def process_batch(session: Session, services_for, *, now: datetime, limit: int = 3) -> list[str]:
    """services_for(snapshot) -> Services. הרשימה נאספת לפני העיבוד כדי לא לחזור על אותה בקשה בסבב."""
    outcomes = []
    for row in stuck_requests(session, now, limit=limit):
        outcomes.append(_release_stuck(session, row, now))
    queued = pending_requests(session, now, limit)
    for row in queued:
        status, _outcome = process_request(session, row, services_for(row["snapshot"]), now=now)
        outcomes.append(status)
    return outcomes


def process_request(
    session: Session,
    row: dict,
    services: Services,
    *,
    now: datetime,
    report=None,
) -> tuple[str, Outcome | None]:
    if row["status"] not in QUEUED_STATUSES:
        return "skipped", None
    bus = build_command_bus(session, build_dispatcher())
    try:
        started = bus.dispatch(StartAssessment(
            command_id=uuid4(),
            request_id=row["request_id"],
            expected_version=row["version"],
            agent_run_id=uuid4(),
            model=services.model_name,
        ))
    except (ConcurrencyError, BusinessRuleViolation):
        return "skipped", None
    try:
        outcome = run_assessment(row["snapshot"], services, today=now.date(), report=report)
    except InfrastructureError as exc:
        bus.dispatch(AbortAssessment(
            command_id=uuid4(),
            request_id=row["request_id"],
            expected_version=started.version,
            reason=f"{exc.service} לא זמין",
        ))
        logger.warning("תשתית לא זמינה: %s", exc.service)
        return "aborted", None
    if outcome.ok and outcome.payload is not None:
        bus.dispatch(CompleteAssessment(
            command_id=uuid4(),
            request_id=row["request_id"],
            expected_version=started.version,
            assessment=outcome.payload,
        ))
        return "completed", outcome
    bus.dispatch(FailAssessment(
        command_id=uuid4(),
        request_id=row["request_id"],
        expected_version=started.version,
        error_code=outcome.error_code or "ASSESSMENT_FAILED",
        message=outcome.message or "ההערכה נכשלה",
        retry_at=(now + _RETRY).isoformat(),
    ))
    return "failed", outcome


def run_request(session: Session, request_id: UUID, services_for, *, now: datetime, report=None) -> tuple[str, Outcome | None]:
    row = request_for_assessment(session, request_id)
    if row is None:
        return "missing", None
    if row["status"] not in QUEUED_STATUSES:
        return "skipped", None
    services = services_for(row["snapshot"])
    return process_request(session, row, services, now=now, report=report)


def _release_stuck(session: Session, row: dict, now: datetime) -> str:
    bus = build_command_bus(session, build_dispatcher())
    try:
        bus.dispatch(FailAssessment(
            command_id=uuid4(),
            request_id=row["request_id"],
            expected_version=row["version"],
            error_code="STUCK_TIMEOUT",
            message="ההערכה נמשכה יותר מ-10 דקות",
            retry_at=(now + _RETRY).isoformat(),
        ))
    except (ConcurrencyError, BusinessRuleViolation):
        return "skipped"
    logger.info("בקשה תקועה הוחזרה לתור: %s", row["request_id"])
    return "released"


def clock() -> datetime:
    return datetime.now(UTC)
