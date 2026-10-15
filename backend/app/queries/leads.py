"""שאילתות דשבורד ולידים של סוכן. קריאה מ-rm_* בלבד."""

from datetime import datetime
from decimal import Decimal
from uuid import UUID

import sqlalchemy as sa
from sqlalchemy.orm import Session

from app.infrastructure.serialization import loads, to_aware_utc, to_naive_utc
from app.infrastructure.tables import (
    rm_agent_kpis,
    rm_agent_product_interest,
    rm_leads,
    rm_products,
    rm_requests,
)
from app.queries.assessments import assessment_view
from app.queries.requests import timeline_items
from app.queries.users import get_user

_PAGE = 20
_SORTS = {
    "aiScore": rm_leads.c.ai_score,
    "amount": rm_leads.c.amount,
    "createdAt": rm_leads.c.created_at,
    "horizonYears": rm_leads.c.horizon_years,
    "status": rm_leads.c.status,
}


def agent_institution(session: Session, user_id: UUID) -> UUID | None:
    user = get_user(session, user_id)
    if user is None or user["role"] != "AGENT" or not user["institutionId"]:
        return None
    return UUID(user["institutionId"])


def dashboard(session: Session, institution_id: UUID) -> dict:
    row = session.execute(
        sa.select(rm_agent_kpis).where(rm_agent_kpis.c.institution_id == institution_id)
    ).mappings().first()
    if row is None:
        return {
            "evaluated": 0,
            "inReview": 0,
            "offerSent": 0,
            "offersSent": 0,
            "offersAccepted": 0,
            "conversionRate": None,
            "averageScore": None,
        }
    sent = int(row["offers_sent"])
    accepted = int(row["offers_accepted"])
    rate = None if sent == 0 else (Decimal(accepted) / Decimal(sent) * Decimal(100)).quantize(Decimal("0.1"))
    average = row["avg_ai_score"]
    return {
        "evaluated": int(row["evaluated_count"]),
        "inReview": int(row["in_review_count"]),
        "offerSent": int(row["offer_sent_count"]),
        "offersSent": sent,
        "offersAccepted": accepted,
        "conversionRate": None if rate is None else format(rate, "f"),
        "averageScore": None if average is None else format(Decimal(average).quantize(Decimal("0.1")), "f"),
    }


def product_interest(session: Session, institution_id: UUID) -> dict:
    products = session.execute(
        sa.select(rm_products.c.product_id, rm_products.c.name)
        .where(rm_products.c.institution_id == institution_id)
        .order_by(rm_products.c.name)
    ).mappings()
    interest = {
        row["product_id"]: row
        for row in session.execute(
            sa.select(rm_agent_product_interest).where(
                rm_agent_product_interest.c.institution_id == institution_id
            )
        ).mappings()
    }
    items = []
    for product in products:
        hit = interest.get(product["product_id"])
        items.append({
            "productId": str(product["product_id"]),
            "name": product["name"],
            "recommended": int(hit["recommended_count"]) if hit else 0,
            "offers": int(hit["offers_count"]) if hit else 0,
            "accepted": int(hit["accepted_count"]) if hit else 0,
        })
    return {"items": items}


def list_leads(
    session: Session,
    institution_id: UUID,
    *,
    status: str | None,
    min_score: int | None,
    goal_type: str | None,
    page: int,
    sort: str | None,
    since: datetime | None,
) -> dict:
    query = sa.select(rm_leads).where(rm_leads.c.institution_id == institution_id)
    if status:
        query = query.where(rm_leads.c.status == status)
    if min_score is not None:
        query = query.where(rm_leads.c.ai_score >= min_score)
    if goal_type:
        query = query.where(rm_leads.c.goal_type == goal_type)
    total = int(session.execute(sa.select(sa.func.count()).select_from(query.subquery())).scalar_one())
    column, descending = _sort(sort)
    ordered = query.order_by(column.desc() if descending else column.asc())
    rows = session.execute(ordered.offset((page - 1) * _PAGE).limit(_PAGE)).mappings()
    return {
        "items": [_lead_summary(row, since) for row in rows],
        "page": page,
        "pageSize": _PAGE,
        "total": total,
    }


def lead_details(session: Session, request_id: UUID, institution_id: UUID, agent_id: UUID) -> dict | None:
    lead = session.execute(
        sa.select(rm_leads).where(
            rm_leads.c.request_id == request_id,
            rm_leads.c.institution_id == institution_id,
        )
    ).mappings().first()
    if lead is None:
        return None
    request = session.execute(
        sa.select(rm_requests).where(rm_requests.c.request_id == request_id)
    ).mappings().one()
    snapshot = loads(request["snapshot"])
    goal = snapshot.get("goal") if isinstance(snapshot, dict) else {}
    risk = snapshot.get("risk") if isinstance(snapshot, dict) else {}
    goal = goal if isinstance(goal, dict) else {}
    risk = risk if isinstance(risk, dict) else {}
    consent = bool(request["consent_share_contact"])
    user = get_user(session, request["investor_id"])
    products = session.execute(
        sa.select(rm_products.c.product_id, rm_products.c.name)
        .where(
            rm_products.c.institution_id == institution_id,
            rm_products.c.is_active == True,
        )
        .order_by(rm_products.c.name)
    ).mappings()
    return {
        "requestId": str(request_id),
        "status": lead["status"],
        "claimedByMe": request["claimed_by"] == agent_id,
        "investor": {
            "displayName": lead["investor_display_name"],
            "email": user["email"] if consent and user else None,
            "phone": user["phone"] if consent and user else None,
        },
        "goal": {
            "title": lead["goal_title"],
            "type": lead["goal_type"],
            "targetAmount": _money(lead["amount"]),
            "initialAmount": _money(goal.get("initial_amount") or 0),
            "monthlyDeposit": _money(goal.get("monthly_deposit") or 0),
            "targetDate": str(goal.get("target_date") or "")[:10],
            "horizonYears": int(lead["horizon_years"]),
            "riskLabel": lead["risk_label"],
            "riskScore": risk.get("score"),
            "liquidityNeed": goal.get("liquidity_need"),
        },
        "aiScore": lead["ai_score"],
        "review": {
            "status": request["assessment_review"],
            "note": request["assessment_note"],
        },
        "assessment": assessment_view(session, request_id, request["assessment_review"]),
        "timeline": timeline_items(session, request_id),
        "products": [
            {"productId": str(row["product_id"]), "name": row["name"]}
            for row in products
        ],
        "createdAt": _iso(lead["created_at"]),
    }


def _lead_summary(row, since: datetime | None) -> dict:
    created = row["created_at"]
    is_new = bool(row["is_new"])
    if since is not None:
        is_new = created > to_naive_utc(since)
    return {
        "requestId": str(row["request_id"]),
        "investorName": row["investor_display_name"],
        "goalTitle": row["goal_title"],
        "goalType": row["goal_type"],
        "amount": _money(row["amount"]),
        "horizonYears": int(row["horizon_years"]),
        "riskLabel": row["risk_label"],
        "aiScore": row["ai_score"],
        "status": row["status"],
        "createdAt": _iso(created),
        "isNew": is_new,
    }


def _sort(raw: str | None) -> tuple:
    field, _, direction = (raw or "createdAt,desc").partition(",")
    column = _SORTS.get(field, rm_leads.c.created_at)
    return column, direction != "asc"


def _money(value) -> str:
    return format(Decimal(str(value)).quantize(Decimal("0.01")), "f")


def _iso(value: datetime) -> str:
    return to_aware_utc(value).isoformat().replace("+00:00", "Z")
