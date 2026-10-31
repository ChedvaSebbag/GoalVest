"""הצעות למשקיע. קריאה מ-rm_offers."""

from uuid import UUID

import sqlalchemy as sa
from sqlalchemy.orm import Session

from app.infrastructure.serialization import loads, to_aware_utc
from app.infrastructure.tables import rm_goals, rm_offers, rm_products, rm_requests, rm_users
from app.reference.institutions import find_institution


def offer_row(session: Session, offer_id: UUID):
    return session.execute(sa.select(rm_offers).where(rm_offers.c.offer_id == offer_id)).mappings().first()


def list_offers(session: Session, investor_id: UUID) -> dict:
    rows = session.execute(
        sa.select(rm_offers)
        .where(rm_offers.c.investor_id == investor_id)
        .order_by(rm_offers.c.created_at.desc())
    ).mappings()
    return {"items": [_view(session, row) for row in rows]}


def get_offer(session: Session, offer_id: UUID, investor_id: UUID) -> dict | None:
    row = session.execute(
        sa.select(rm_offers).where(
            rm_offers.c.offer_id == offer_id,
            rm_offers.c.investor_id == investor_id,
        )
    ).mappings().first()
    if row is None:
        return None
    return _view(session, row)


def pending_offer_count(session: Session, investor_id: UUID) -> int:
    return int(session.execute(
        sa.select(sa.func.count()).select_from(rm_offers).where(
            rm_offers.c.investor_id == investor_id,
            rm_offers.c.status == "SENT",
        )
    ).scalar_one())


def _view(session: Session, row) -> dict:
    items = loads(row["items_json"])
    if not isinstance(items, list):
        items = []
    ids = [UUID(str(item["product_id"])) for item in items if isinstance(item, dict) and item.get("product_id")]
    names = {}
    if ids:
        found = session.execute(
            sa.select(rm_products.c.product_id, rm_products.c.name).where(rm_products.c.product_id.in_(ids))
        ).mappings()
        names = {item["product_id"]: item["name"] for item in found}
    agent = session.execute(
        sa.select(rm_users.c.full_name).where(rm_users.c.user_id == row["agent_id"])
    ).scalar_one_or_none()
    goal_title = session.execute(
        sa.select(rm_goals.c.title)
        .select_from(rm_requests.join(rm_goals, rm_goals.c.goal_id == rm_requests.c.goal_id))
        .where(rm_requests.c.request_id == row["request_id"])
    ).scalar_one_or_none()
    institution = find_institution(row["institution_id"])
    return {
        "offerId": str(row["offer_id"]),
        "requestId": str(row["request_id"]),
        "status": row["status"],
        "message": row["message"],
        "createdAt": to_aware_utc(row["created_at"]).isoformat().replace("+00:00", "Z"),
        "agentName": agent or "סוכן",
        "institutionName": institution.name if institution else "",
        "goalTitle": goal_title or "",
        "items": [
            {
                "productId": str(item["product_id"]),
                "name": names.get(UUID(str(item["product_id"])), ""),
                "percent": item.get("percent"),
            }
            for item in items
            if isinstance(item, dict) and item.get("product_id")
        ],
    }

