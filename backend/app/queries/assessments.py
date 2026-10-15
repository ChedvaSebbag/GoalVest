"""תור ההערכה וההערכה השמורה. קריאה מ-rm_* בלבד."""

from datetime import datetime, timedelta
from uuid import UUID

import sqlalchemy as sa
from sqlalchemy.orm import Session

from app.infrastructure.serialization import loads, to_naive_utc
from app.infrastructure.tables import event_store, rm_assessments, rm_products, rm_requests

_CHANNEL_KEYS = (
    ("capital_market", "capitalMarket"),
    ("hishtalmut", "hishtalmut"),
    ("gemel_policy", "gemelPolicy"),
)


QUEUED_STATUSES = ("SUBMITTED", "REEVALUATION_REQUESTED")


def pending_requests(session: Session, now: datetime, limit: int = 3) -> list[dict]:
    moment = to_naive_utc(now)
    version = _version()
    rows = session.execute(
        _columns(version)
        .where(
            rm_requests.c.status.in_(QUEUED_STATUSES),
            sa.or_(rm_requests.c.retry_at.is_(None), rm_requests.c.retry_at <= moment),
        )
        .order_by(rm_requests.c.updated_at)
        .limit(limit)
    ).mappings()
    return [_row(row) for row in rows]


def stuck_requests(session: Session, now: datetime, *, minutes: int = 10, limit: int = 3) -> list[dict]:
    cutoff = to_naive_utc(now) - timedelta(minutes=minutes)
    version = _version()
    rows = session.execute(
        _columns(version)
        .where(rm_requests.c.status == "AI_PROCESSING", rm_requests.c.updated_at < cutoff)
        .order_by(rm_requests.c.updated_at)
        .limit(limit)
    ).mappings()
    return [_row(row) for row in rows]


def request_for_assessment(session: Session, request_id: UUID) -> dict | None:
    version = _version()
    row = session.execute(_columns(version).where(rm_requests.c.request_id == request_id)).mappings().first()
    if row is None:
        return None
    return _row(row)


def assessment_view(session: Session, request_id: UUID, review: str | None) -> dict | None:
    row = session.execute(
        sa.select(rm_assessments)
        .where(rm_assessments.c.request_id == request_id)
        .order_by(rm_assessments.c.attempt.desc())
    ).mappings().first()
    if row is None:
        return None
    payload = loads(row["assessment"])
    if not isinstance(payload, dict):
        return None
    products = _products(session, payload.get("recommended_products") or [])
    return {
        "overallScore": payload.get("overall_score"),
        "channelScores": _channels(payload.get("channel_scores") or {}),
        "allocation": _channels(payload.get("allocation") or {}),
        "recommendedProducts": products,
        "rationale": payload.get("rationale") or "",
        "riskFlags": [
            {"code": flag.get("code"), "severity": flag.get("severity"), "text": flag.get("text")}
            for flag in payload.get("risk_flags") or []
            if isinstance(flag, dict)
        ],
        "sources": [
            {
                "type": source.get("type"),
                "title": source.get("title") or "",
                "url": source.get("url"),
                "excerpt": source.get("excerpt"),
            }
            for source in payload.get("sources") or []
            if isinstance(source, dict)
        ],
        "pendingReview": review is None,
        "model": payload.get("model"),
        "durationMs": payload.get("duration_ms"),
    }


def _version():
    return (
        sa.select(sa.func.max(event_store.c.version))
        .where(
            event_store.c.aggregate_id == rm_requests.c.request_id,
            event_store.c.aggregate_type == "InvestmentRequest",
        )
        .scalar_subquery()
    )


def _columns(version):
    return sa.select(
        rm_requests.c.request_id,
        rm_requests.c.status,
        rm_requests.c.snapshot,
        rm_requests.c.updated_at,
        rm_requests.c.assessment_review,
        version.label("version"),
    )


def _row(row) -> dict:
    snapshot = loads(row["snapshot"])
    return {
        "request_id": row["request_id"],
        "status": row["status"],
        "snapshot": snapshot if isinstance(snapshot, dict) else {},
        "updated_at": row["updated_at"],
        "version": int(row["version"] or 0),
        "assessment_review": row["assessment_review"],
    }


def _channels(block: dict) -> dict:
    return {camel: block.get(snake) for snake, camel in _CHANNEL_KEYS}


def _products(session: Session, items: list) -> list[dict]:
    ids = []
    for item in items:
        if isinstance(item, dict) and item.get("product_id"):
            ids.append(UUID(str(item["product_id"])))
    names = {}
    if ids:
        found = session.execute(
            sa.select(rm_products.c.product_id, rm_products.c.name).where(rm_products.c.product_id.in_(ids))
        ).mappings()
        names = {row["product_id"]: row["name"] for row in found}
    viewed = []
    for item in items:
        if not isinstance(item, dict):
            continue
        product_id = UUID(str(item["product_id"]))
        viewed.append({
            "productId": str(product_id),
            "name": names.get(product_id) or "",
            "fitScore": item.get("fit_score"),
            "reason": item.get("reason") or "",
        })
    return viewed
