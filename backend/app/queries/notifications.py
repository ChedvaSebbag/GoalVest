"""התראות משתמש. קריאה מ-rm_notifications."""

from uuid import UUID

import sqlalchemy as sa
from sqlalchemy.orm import Session

from app.infrastructure.serialization import to_aware_utc
from app.infrastructure.tables import rm_notifications


def notification_row(session: Session, notification_id: UUID):
    return session.execute(
        sa.select(rm_notifications).where(rm_notifications.c.notification_id == notification_id)
    ).mappings().first()


def list_notifications(session: Session, user_id: UUID, *, unread_only: bool) -> dict:
    query = sa.select(rm_notifications).where(rm_notifications.c.user_id == user_id)
    if unread_only:
        query = query.where(rm_notifications.c.is_read == False)
    rows = session.execute(query.order_by(rm_notifications.c.created_at.desc())).mappings()
    return {"items": [_view(row) for row in rows]}


def unread_count(session: Session, user_id: UUID) -> dict:
    total = session.execute(
        sa.select(sa.func.count()).select_from(rm_notifications).where(
            rm_notifications.c.user_id == user_id,
            rm_notifications.c.is_read == False,
        )
    ).scalar_one()
    return {"count": int(total)}


def _view(row) -> dict:
    return {
        "id": str(row["notification_id"]),
        "title": row["title"],
        "body": row["body"],
        "link": row["link"],
        "isRead": bool(row["is_read"]),
        "createdAt": to_aware_utc(row["created_at"]).isoformat().replace("+00:00", "Z"),
    }
