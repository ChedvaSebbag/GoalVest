"""קריאה מ-rm_goals ומבקשה הפעילה. אין טעינת Aggregate."""

from datetime import date
from decimal import Decimal
from uuid import UUID

import sqlalchemy as sa
from sqlalchemy.orm import Session

from app.infrastructure.serialization import loads
from app.infrastructure.tables import rm_goals, rm_requests
from app.queries.assessments import assessment_view
from app.queries.offers import pending_offer_count


def find_active_request(session: Session, goal_id: UUID):
    goal = session.execute(sa.select(rm_goals).where(rm_goals.c.goal_id == goal_id)).mappings().first()
    if goal is None or goal["active_request_id"] is None:
        return None
    return session.execute(
        sa.select(rm_requests).where(rm_requests.c.request_id == goal["active_request_id"])
    ).mappings().one()


def list_goals(session: Session, investor_id: UUID) -> dict:
    rows = session.execute(
        sa.select(rm_goals)
        .where(rm_goals.c.investor_id == investor_id, rm_goals.c.status == "ACTIVE")
        .order_by(rm_goals.c.updated_at.desc())
    ).mappings()
    return {"items": [_summary(session, row) for row in rows]}


def get_goal(session: Session, goal_id: UUID, investor_id: UUID) -> dict | None:
    row = session.execute(
        sa.select(rm_goals).where(rm_goals.c.goal_id == goal_id, rm_goals.c.investor_id == investor_id)
    ).mappings().first()
    if row is None:
        return None
    summary = _summary(session, row)
    if summary["activeRequestId"] is None:
        latest = session.execute(
            sa.select(rm_requests.c.request_id, rm_requests.c.status, rm_requests.c.consent_share_contact)
            .where(rm_requests.c.goal_id == goal_id)
            .order_by(rm_requests.c.updated_at.desc())
        ).mappings().first()
        if latest is not None:
            summary["activeRequestId"] = str(latest["request_id"])
            summary["requestStatus"] = latest["status"]
            summary["consentShareContact"] = latest["consent_share_contact"]
    summary.update({
        "initialAmount": _money(row["initial_amount"]),
        "monthlyDeposit": _money(row["monthly_deposit"]),
        "flexibility": row["flexibility"],
        "liquidityNeed": row["liquidity_need"],
        "excludedChannels": loads(row["excluded_channels"]),
        "preferredChannels": loads(row["preferred_channels"]),
        "preferredInstitutions": loads(row["preferred_institutions"]),
        "assessment": None,
    })
    request_id = summary["activeRequestId"]
    if request_id is not None:
        review = session.execute(
            sa.select(rm_requests.c.assessment_review).where(rm_requests.c.request_id == UUID(request_id))
        ).scalar_one_or_none()
        summary["assessment"] = assessment_view(session, UUID(request_id), review)
    return summary


def investor_dashboard(session: Session, investor_id: UUID) -> dict:
    rows = session.execute(
        sa.select(rm_goals)
        .where(rm_goals.c.investor_id == investor_id, rm_goals.c.status == "ACTIVE")
        .order_by(rm_goals.c.updated_at.desc())
    ).mappings()
    goals = []
    planned = Decimal(0)
    for row in rows:
        planned += Decimal(row["target_amount"])
        summary = _summary(session, row)
        target = Decimal(row["target_amount"])
        progress = Decimal(0)
        if target > 0:
            progress = (Decimal(row["initial_amount"]) / target * Decimal(100)).quantize(Decimal("0.1"))
            if progress > Decimal(100):
                progress = Decimal("100.0")
        assessment = None
        if summary["activeRequestId"] is not None:
            review = session.execute(
                sa.select(rm_requests.c.assessment_review).where(
                    rm_requests.c.request_id == UUID(summary["activeRequestId"])
                )
            ).scalar_one_or_none()
            assessment = assessment_view(session, UUID(summary["activeRequestId"]), review)
        summary.update({
            "initialAmount": _money(row["initial_amount"]),
            "progress": format(progress, "f"),
            "assessment": assessment,
        })
        goals.append(summary)
    return {
        "plannedCapital": _money(planned),
        "activeGoals": len(goals),
        "pendingOffers": pending_offer_count(session, investor_id),
        "goals": goals,
    }


def _summary(session: Session, row) -> dict:
    request_status = None
    consent = None
    if row["active_request_id"] is not None:
        request = session.execute(
            sa.select(rm_requests.c.status, rm_requests.c.consent_share_contact).where(
                rm_requests.c.request_id == row["active_request_id"]
            )
        ).mappings().first()
        if request is not None:
            request_status = request["status"]
            consent = request["consent_share_contact"]
    return {
        "goalId": str(row["goal_id"]),
        "title": row["title"],
        "type": row["type"],
        "targetAmount": _money(row["target_amount"]),
        "targetDate": _date(row["target_date"]),
        "status": row["status"],
        "requestStatus": request_status,
        "activeRequestId": str(row["active_request_id"]) if row["active_request_id"] else None,
        "consentShareContact": consent,
    }


def _money(value: Decimal) -> str:
    return format(Decimal(value).quantize(Decimal("0.01")), "f")


def _date(value: date) -> str:
    return value.isoformat() if isinstance(value, date) else str(value)
