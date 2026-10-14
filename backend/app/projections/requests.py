"""InvestmentRequestSubmitted ו-RequestCancelled אל rm_requests, rm_goals וציר הזמן."""

from uuid import UUID

import sqlalchemy as sa
from goalvest_core import Event
from sqlalchemy.orm import Session

from app.infrastructure.serialization import to_naive_utc
from app.infrastructure.tables import event_store, rm_goals, rm_request_timeline, rm_requests
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


def _cancel_text(reason: str) -> str:
    if reason == "GOAL_UPDATED":
        return "הבקשה נסגרה בעקבות עדכון היעד"
    if reason == "GOAL_ARCHIVED":
        return "הבקשה נסגרה כי היעד הועבר לארכיון"
    return "הבקשה בוטלה"


def _timeline(session: Session, event: Event, text: str) -> None:
    position = session.execute(
        sa.select(event_store.c.global_position).where(event_store.c.event_id == event.event_id)
    ).scalar_one()
    session.execute(
        sa.insert(rm_request_timeline).values(
            request_id=event.aggregate_id,
            global_position=position,
            event_type=event.event_type,
            actor="משקיע",
            display_text=text,
            occurred_at=to_naive_utc(event.occurred_at),
        )
    )
