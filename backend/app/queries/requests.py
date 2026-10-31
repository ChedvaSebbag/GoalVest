"""ציר זמן ושורת בקשה מ-rm_requests. אין טעינת Aggregate."""

from uuid import UUID

import sqlalchemy as sa
from sqlalchemy.orm import Session

from app.infrastructure.serialization import to_aware_utc
from app.infrastructure.tables import rm_request_timeline, rm_requests


def get_request_row(session: Session, request_id: UUID):
    return session.execute(
        sa.select(rm_requests).where(rm_requests.c.request_id == request_id)
    ).mappings().first()


def timeline_for(session: Session, request_id: UUID, investor_id: UUID) -> dict | None:
    owner = session.execute(
        sa.select(rm_requests.c.request_id).where(
            rm_requests.c.request_id == request_id,
            rm_requests.c.investor_id == investor_id,
        )
    ).first()
    if owner is None:
        return None
    return {"items": timeline_items(session, request_id)}


def timeline_items(session: Session, request_id: UUID) -> list[dict]:
    rows = session.execute(
        sa.select(rm_request_timeline)
        .where(rm_request_timeline.c.request_id == request_id)
        .order_by(rm_request_timeline.c.global_position)
    ).mappings()
    return [
        {
            "eventType": row["event_type"],
            "displayText": row["display_text"],
            "actor": row["actor"],
            "occurredAt": to_aware_utc(row["occurred_at"]).isoformat().replace("+00:00", "Z"),
        }
        for row in rows
    ]
