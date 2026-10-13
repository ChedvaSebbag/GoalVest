"""קריאה מ-rm_users בלבד: קיום אימייל, התחברות ופרופיל."""

from uuid import UUID

import sqlalchemy as sa
from goalvest_core.accounts import normalize_email
from sqlalchemy.orm import Session

from app.auth.passwords import verify_or_dummy
from app.infrastructure.tables import rm_users


def email_exists(session: Session, email: str) -> bool:
    normalized = normalize_email(email)
    row = session.execute(
        sa.select(rm_users.c.user_id).where(rm_users.c.email == normalized)
    ).first()
    return row is not None


def authenticate(session: Session, email: str, password: str) -> dict | None:
    normalized = normalize_email(email)
    row = session.execute(sa.select(rm_users).where(rm_users.c.email == normalized)).mappings().first()
    password_hash = row["password_hash"] if row is not None else None
    if not verify_or_dummy(password, password_hash) or row is None:
        return None
    return _profile(row)


def get_user(session: Session, user_id: UUID) -> dict | None:
    row = session.execute(sa.select(rm_users).where(rm_users.c.user_id == user_id)).mappings().first()
    if row is None:
        return None
    return _profile(row)


def _profile(row: sa.RowMapping) -> dict:
    institution = row["institution_id"]
    return {
        "id": str(row["user_id"]),
        "email": row["email"],
        "fullName": row["full_name"],
        "phone": row["phone"],
        "role": row["role"],
        "institutionId": str(institution) if institution is not None else None,
        "status": row["status"],
    }
