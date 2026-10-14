"""אירועי InvestmentRequest אל rm_requests, rm_assessments, rm_goals וציר הזמן."""

from datetime import datetime
from uuid import UUID

import sqlalchemy as sa
from goalvest_core import Event
from sqlalchemy.orm import Session

from app.infrastructure.serialization import to_naive_utc
from app.infrastructure.tables import event_store, rm_assessments, rm_goals, rm_request_timeline, rm_requests
from app.projections.values import as_json


def project_request_submitted(event: Event, session: Session) -> None:
    payload = event.payload
    occurred = to_naive_utc(event.occurred_at)
    session.execute(
        sa.insert(rm_requests).values(
            request_id=event.aggregate_id,
            goal_id=UUID(str(payload["goal_id"])),
            investor_id=UUID(str(payload["investor_id"])),
            status="SUBMITTED",
            consent_share_contact=True,
            snapshot=as_json(payload["snapshot"]),
            overall_score=None,
            claimed_by=None,
            institution_id=None,
            assessment_review=None,
            created_at=occurred,
            updated_at=occurred,
        )
    )
    session.execute(
        sa.update(rm_goals)
        .where(rm_goals.c.goal_id == UUID(str(payload["goal_id"])))
        .values(active_request_id=event.aggregate_id, updated_at=occurred)
    )
    _timeline(session, event, "הבקשה הוגשה")


def project_request_cancelled(event: Event, session: Session) -> None:
    occurred = to_naive_utc(event.occurred_at)
    session.execute(
        sa.update(rm_requests)
        .where(rm_requests.c.request_id == event.aggregate_id)
        .values(status="CANCELLED", updated_at=occurred)
    )
    session.execute(
        sa.update(rm_goals)
        .where(rm_goals.c.active_request_id == event.aggregate_id)
        .values(active_request_id=None, updated_at=occurred)
    )
    _timeline(session, event, _cancel_text(event.payload.get("reason") or ""))


def project_assessment_started(event: Event, session: Session) -> None:
    _touch(session, event, status="AI_PROCESSING", retry_at=None)
    _timeline(session, event, "ההערכה האוטומטית התחילה", actor="סוכן AI")


def project_assessment_completed(event: Event, session: Session) -> None:
    occurred = to_naive_utc(event.occurred_at)
    score = event.payload.get("overall_score")
    _touch(session, event, status="AI_EVALUATED", overall_score=score, retry_at=None)
    session.execute(
        sa.insert(rm_assessments).values(
            request_id=event.aggregate_id,
            attempt=_attempt(event),
            assessment=as_json(event.payload),
            created_at=occurred,
        )
    )
    _timeline(session, event, "ההערכה האוטומטית הושלמה", actor="סוכן AI")


def project_assessment_failed(event: Event, session: Session) -> None:
    attempt = int(event.payload["attempt"])
    status = "FAILED" if attempt >= 3 else "SUBMITTED"
    _touch(session, event, status=status, retry_at=_retry(event.payload.get("retry_at")))
    text = "ההערכה נכשלה" if status == "FAILED" else "ההערכה לא הושלמה ותחזור לתור"
    _timeline(session, event, text, actor="סוכן AI")


def project_assessment_aborted(event: Event, session: Session) -> None:
    _touch(session, event, status="SUBMITTED", retry_at=None)
    _timeline(session, event, "ההערכה הופסקה בגלל תקלת תשתית ותחזור לתור", actor="סוכן AI")


def _cancel_text(reason: str) -> str:
    if reason == "GOAL_UPDATED":
        return "הבקשה נסגרה בעקבות עדכון היעד"
    if reason == "GOAL_ARCHIVED":
        return "הבקשה נסגרה כי היעד הועבר לארכיון"
    return "הבקשה בוטלה"


def _touch(session: Session, event: Event, **values) -> None:
    values["updated_at"] = to_naive_utc(event.occurred_at)
    session.execute(
        sa.update(rm_requests).where(rm_requests.c.request_id == event.aggregate_id).values(**values)
    )


def _attempt(event: Event) -> int:
    raw = event.payload.get("attempt")
    if raw is None:
        return 1
    return int(raw)


def _retry(value: object) -> datetime | None:
    if not value:
        return None
    parsed = datetime.fromisoformat(str(value))
    return to_naive_utc(parsed)


def _timeline(session: Session, event: Event, text: str, actor: str = "משקיע") -> None:
    position = session.execute(
        sa.select(event_store.c.global_position).where(event_store.c.event_id == event.event_id)
    ).scalar_one()
    session.execute(
        sa.insert(rm_request_timeline).values(
            request_id=event.aggregate_id,
            global_position=position,
            event_type=event.event_type,
            actor=actor,
            display_text=text,
            occurred_at=to_naive_utc(event.occurred_at),
        )
    )
