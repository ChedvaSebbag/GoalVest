"""Projector של UserRegistered אל rm_users. ראו docs/07 §7.4."""

from uuid import UUID

import sqlalchemy as sa
from goalvest_core import Event
from sqlalchemy.orm import Session

from app.infrastructure.tables import rm_users


def project_user_registered(event: Event, session: Session) -> None:
    payload = event.payload
    raw_institution = payload.get("institution_id")
    institution = UUID(raw_institution) if raw_institution else None
    session.execute(
        sa.insert(rm_users).values(
            user_id=event.aggregate_id,
            email=payload["email"],
            full_name=payload["full_name"],
            phone=payload["phone"],
            role=payload["role"],
            institution_id=institution,
            status="ACTIVE",
            password_hash=payload["password_hash"],
        )
    )
