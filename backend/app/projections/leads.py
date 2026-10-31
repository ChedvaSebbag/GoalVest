"""לידים, מדדי סוכן, הצעות והתראות. נגזרים מאירועי InvestmentRequest."""

from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

import sqlalchemy as sa
from goalvest_core import Event
from sqlalchemy.orm import Session

from app.infrastructure.serialization import loads, to_naive_utc
from app.infrastructure.tables import (
    event_store,
    rm_agent_kpis,
    rm_agent_product_interest,
    rm_assessments,
    rm_leads,
    rm_notifications,
    rm_offers,
    rm_products,
    rm_request_timeline,
    rm_requests,
    rm_users,
)
from app.projections.values import as_date, as_json, as_money

ANONYMOUS = "משקיע אנונימי"


def project_lead_claimed(event: Event, session: Session) -> None:
    occurred = to_naive_utc(event.occurred_at)
    agent_id = UUID(str(event.payload["agent_id"]))
    institution_id = UUID(str(event.payload["institution_id"]))
    session.execute(
        sa.update(rm_requests)
        .where(rm_requests.c.request_id == event.aggregate_id)
        .values(
            status="IN_REVIEW",
            claimed_by=agent_id,
            institution_id=institution_id,
            updated_at=occurred,
        )
    )
    _set_status(session, event.aggregate_id, "IN_REVIEW", occurred)
    _timeline(session, event, "סוכן לקח את הליד", _name(session, agent_id, "סוכן"))
    _refresh_for_request(session, event.aggregate_id, occurred)


def project_assessment_approved(event: Event, session: Session) -> None:
    note = (event.payload.get("note") or "").strip() or None
    session.execute(
        sa.update(rm_requests)
        .where(rm_requests.c.request_id == event.aggregate_id)
        .values(
            assessment_review="approved",
            assessment_note=note,
            updated_at=to_naive_utc(event.occurred_at),
        )
    )
    _timeline(session, event, "הסוכן אישר את ההערכה", _name(session, event.payload.get("agent_id"), "סוכן"))


def project_assessment_rejected(event: Event, session: Session) -> None:
    session.execute(
        sa.update(rm_requests)
        .where(rm_requests.c.request_id == event.aggregate_id)
        .values(
            assessment_review="rejected",
            assessment_note=event.payload.get("note"),
            updated_at=to_naive_utc(event.occurred_at),
        )
    )
    _timeline(session, event, "הסוכן דחה את ההערכה", _name(session, event.payload.get("agent_id"), "סוכן"))


def project_reevaluation_requested(event: Event, session: Session) -> None:
    occurred = to_naive_utc(event.occurred_at)
    session.execute(
        sa.update(rm_requests)
        .where(rm_requests.c.request_id == event.aggregate_id)
        .values(
            status="REEVALUATION_REQUESTED",
            claimed_by=None,
            institution_id=None,
            assessment_review=None,
            assessment_note=None,
            updated_at=occurred,
        )
    )
    _set_status(session, event.aggregate_id, "REEVALUATION_REQUESTED", occurred)
    _timeline(session, event, "הסוכן ביקש הערכה מחדש", _name(session, event.payload.get("agent_id"), "סוכן"))
    _refresh_for_request(session, event.aggregate_id, occurred)


def project_offer_sent(event: Event, session: Session) -> None:
    occurred = to_naive_utc(event.occurred_at)
    request = _request(session, event.aggregate_id)
    if request is None:
        return
    offer_id = UUID(str(event.payload["offer_id"]))
    agent_id = UUID(str(event.payload["agent_id"]))
    institution_id = request["institution_id"]
    items = event.payload.get("items") or []
    session.execute(
        sa.update(rm_requests)
        .where(rm_requests.c.request_id == event.aggregate_id)
        .values(status="OFFER_SENT", updated_at=occurred)
    )
    _set_status(session, event.aggregate_id, "OFFER_SENT", occurred)
    session.execute(
        sa.insert(rm_offers).values(
            offer_id=offer_id,
            request_id=event.aggregate_id,
            investor_id=request["investor_id"],
            agent_id=agent_id,
            institution_id=institution_id,
            items_json=as_json(items),
            message=str(event.payload.get("message") or "")[:4000],
            status="SENT",
            created_at=occurred,
            updated_at=occurred,
        )
    )
    for product_id in _product_ids(items):
        _bump_interest(session, product_id, offers=1, accepted=0)
    message = str(event.payload.get("message") or "").strip()
    session.execute(
        sa.insert(rm_notifications).values(
            notification_id=offer_id,
            user_id=request["investor_id"],
            title="התקבלה הצעה",
            body=(message or "סוכן שלח הצעה ליעד שלך.")[:1000],
            link=f"/investor/offers/{offer_id}",
            is_read=False,
            created_at=occurred,
        )
    )
    _timeline(session, event, "נשלחה הצעה", _name(session, agent_id, "סוכן"))
    _refresh_for_request(session, event.aggregate_id, occurred)


def project_offer_accepted(event: Event, session: Session) -> None:
    occurred = to_naive_utc(event.occurred_at)
    offer_id = UUID(str(event.payload["offer_id"]))
    session.execute(
        sa.update(rm_requests)
        .where(rm_requests.c.request_id == event.aggregate_id)
        .values(status="ACCEPTED", updated_at=occurred)
    )
    _set_status(session, event.aggregate_id, "ACCEPTED", occurred)
    offer = _offer(session, offer_id)
    session.execute(
        sa.update(rm_offers).where(rm_offers.c.offer_id == offer_id).values(status="ACCEPTED", updated_at=occurred)
    )
    if offer is not None:
        for product_id in _product_ids(loads(offer["items_json"])):
            _bump_interest(session, product_id, offers=0, accepted=1)
    _timeline(session, event, "ההצעה התקבלה", "משקיע")
    _refresh_for_request(session, event.aggregate_id, occurred)


def project_offer_declined(event: Event, session: Session) -> None:
    occurred = to_naive_utc(event.occurred_at)
    offer_id = UUID(str(event.payload["offer_id"]))
    session.execute(
        sa.update(rm_requests)
        .where(rm_requests.c.request_id == event.aggregate_id)
        .values(status="IN_REVIEW", updated_at=occurred)
    )
    _set_status(session, event.aggregate_id, "IN_REVIEW", occurred)
    session.execute(
        sa.update(rm_offers).where(rm_offers.c.offer_id == offer_id).values(status="DECLINED", updated_at=occurred)
    )
    _timeline(session, event, "ההצעה נדחתה", "משקיע")
    _refresh_for_request(session, event.aggregate_id, occurred)


def project_notification_read(event: Event, session: Session) -> None:
    session.execute(
        sa.update(rm_notifications)
        .where(rm_notifications.c.notification_id == event.aggregate_id)
        .values(is_read=True)
    )


def sync_leads_after_assessment(session: Session, event: Event) -> None:
    """מחליף את שורות הליד של הבקשה לפי ההמלצה שנשמרה עכשיו."""
    request = _request(session, event.aggregate_id)
    if request is None:
        return
    occurred = to_naive_utc(event.occurred_at)
    previous_institutions = _lead_institutions(session, event.aggregate_id)
    previous = _previous_products(session, event.aggregate_id)
    current = _product_ids(event.payload.get("recommended_products") or [])
    _replace_leads(session, request, occurred)
    _retarget(session, previous, current)
    for institution_id in previous_institutions | _lead_institutions(session, event.aggregate_id):
        _refresh_kpis(session, institution_id, occurred)


def sync_lead_status(session: Session, request_id: UUID, status: str, occurred: datetime) -> None:
    _set_status(session, request_id, status, occurred)
    _refresh_for_request(session, request_id, occurred)


def rebuild_agent_views(session: Session) -> int:
    """בונה לידים ומדדים מההערכות וההצעות שכבר בטבלאות הקריאה."""
    session.execute(sa.delete(rm_leads))
    session.execute(sa.delete(rm_agent_kpis))
    session.execute(sa.delete(rm_agent_product_interest))
    requests = session.execute(sa.select(rm_requests)).mappings()
    count = 0
    institutions: set[UUID] = set()
    for request in requests:
        added = _replace_leads(session, request, request["updated_at"])
        count += added
    for row in session.execute(sa.select(rm_leads.c.institution_id)).scalars():
        institutions.add(row)
    _recompute_recommendations(session)
    _recompute_offer_counts(session)
    for row in session.execute(sa.select(rm_offers.c.institution_id)).scalars():
        institutions.add(row)
    moment = to_naive_utc(datetime.now(UTC))
    for institution_id in institutions:
        _refresh_kpis(session, institution_id, moment)
    return count


def _replace_leads(session: Session, request, occurred: datetime) -> int:
    assessment = _latest_assessment(session, request["request_id"])
    if assessment is None:
        return 0
    payload = loads(assessment["assessment"])
    if not isinstance(payload, dict):
        return 0
    product_ids = _product_ids(payload.get("recommended_products") or [])
    institutions = _institutions(session, product_ids)
    session.execute(sa.delete(rm_leads).where(rm_leads.c.request_id == request["request_id"]))
    if not institutions:
        return 0
    fields = _lead_fields(session, request, payload, occurred)
    for institution_id in institutions:
        session.execute(
            sa.insert(rm_leads).values(institution_id=institution_id, **fields)
        )
    return len(institutions)


def _lead_fields(session: Session, request, payload: dict, occurred: datetime) -> dict:
    snapshot = loads(request["snapshot"])
    goal = snapshot.get("goal") if isinstance(snapshot, dict) else {}
    risk = snapshot.get("risk") if isinstance(snapshot, dict) else {}
    goal = goal if isinstance(goal, dict) else {}
    risk = risk if isinstance(risk, dict) else {}
    target = as_date(goal.get("target_date") or occurred.date())
    days = (target - occurred.date()).days
    score = payload.get("overall_score")
    return {
        "request_id": request["request_id"],
        "investor_id": request["investor_id"],
        "investor_display_name": _display_name(session, request),
        "goal_type": str(goal.get("type") or "")[:30],
        "goal_title": str(goal.get("title") or "")[:200],
        "amount": as_money(goal.get("target_amount") or 0),
        "horizon_years": max(days // 365, 0),
        "risk_label": str(risk.get("label") or "")[:40],
        "ai_score": int(score) if score is not None else None,
        "status": request["status"],
        "is_new": True,
        "created_at": occurred,
        "updated_at": occurred,
    }


def _display_name(session: Session, request) -> str:
    if not request["consent_share_contact"]:
        return ANONYMOUS
    return _name(session, request["investor_id"], ANONYMOUS)[:200]


def _previous_products(session: Session, request_id: UUID) -> list[UUID]:
    rows = session.execute(
        sa.select(rm_assessments.c.assessment)
        .where(rm_assessments.c.request_id == request_id)
        .order_by(rm_assessments.c.attempt.desc())
        .limit(2)
    ).scalars().all()
    if len(rows) < 2:
        return []
    payload = loads(rows[1])
    if not isinstance(payload, dict):
        return []
    return _product_ids(payload.get("recommended_products") or [])


def _recompute_recommendations(session: Session) -> None:
    latest: dict[UUID, str] = {}
    rows = session.execute(
        sa.select(rm_assessments.c.request_id, rm_assessments.c.attempt, rm_assessments.c.assessment)
        .order_by(rm_assessments.c.attempt)
    ).mappings()
    for row in rows:
        latest[row["request_id"]] = row["assessment"]
    for raw in latest.values():
        payload = loads(raw)
        if isinstance(payload, dict):
            for product_id in _product_ids(payload.get("recommended_products") or []):
                _bump_interest(session, product_id, offers=0, accepted=0, recommended=1)


def _recompute_offer_counts(session: Session) -> None:
    for offer in session.execute(sa.select(rm_offers)).mappings():
        accepted = 1 if offer["status"] == "ACCEPTED" else 0
        for product_id in _product_ids(loads(offer["items_json"])):
            _bump_interest(session, product_id, offers=1, accepted=accepted)


def _retarget(session: Session, previous: list[UUID], current: list[UUID]) -> None:
    before = set(previous)
    after = set(current)
    for product_id in before - after:
        _bump_interest(session, product_id, offers=0, accepted=0, recommended=-1)
    for product_id in after - before:
        _bump_interest(session, product_id, offers=0, accepted=0, recommended=1)


def _bump_interest(session: Session, product_id: UUID, *, offers: int, accepted: int, recommended: int = 0) -> None:
    institution_id = session.execute(
        sa.select(rm_products.c.institution_id).where(rm_products.c.product_id == product_id)
    ).scalar_one_or_none()
    if institution_id is None:
        return
    row = session.execute(
        sa.select(rm_agent_product_interest).where(rm_agent_product_interest.c.product_id == product_id)
    ).mappings().first()
    if row is None:
        if recommended < 0:
            return
        session.execute(
            sa.insert(rm_agent_product_interest).values(
                product_id=product_id,
                institution_id=institution_id,
                recommended_count=max(recommended, 0),
                offers_count=offers,
                accepted_count=accepted,
            )
        )
        return
    session.execute(
        sa.update(rm_agent_product_interest)
        .where(rm_agent_product_interest.c.product_id == product_id)
        .values(
            recommended_count=max(int(row["recommended_count"]) + recommended, 0),
            offers_count=int(row["offers_count"]) + offers,
            accepted_count=int(row["accepted_count"]) + accepted,
        )
    )


def _refresh_for_request(session: Session, request_id: UUID, occurred: datetime) -> None:
    institutions = session.execute(
        sa.select(rm_leads.c.institution_id).where(rm_leads.c.request_id == request_id)
    ).scalars()
    seen = set(institutions)
    request = _request(session, request_id)
    if request is not None and request["institution_id"] is not None:
        seen.add(request["institution_id"])
    for institution_id in seen:
        _refresh_kpis(session, institution_id, occurred)


def _refresh_kpis(session: Session, institution_id: UUID, occurred: datetime) -> None:
    counts = {
        row["status"]: int(row["total"])
        for row in session.execute(
            sa.select(rm_leads.c.status, sa.func.count().label("total"))
            .where(rm_leads.c.institution_id == institution_id)
            .group_by(rm_leads.c.status)
        ).mappings()
    }
    average = session.execute(
        sa.select(sa.func.avg(rm_leads.c.ai_score)).where(
            rm_leads.c.institution_id == institution_id,
            rm_leads.c.ai_score.is_not(None),
        )
    ).scalar_one()
    offers_sent = int(session.execute(
        sa.select(sa.func.count()).select_from(rm_offers).where(rm_offers.c.institution_id == institution_id)
    ).scalar_one())
    offers_accepted = int(session.execute(
        sa.select(sa.func.count()).select_from(rm_offers).where(
            rm_offers.c.institution_id == institution_id,
            rm_offers.c.status == "ACCEPTED",
        )
    ).scalar_one())
    values = {
        "evaluated_count": counts.get("AI_EVALUATED", 0),
        "in_review_count": counts.get("IN_REVIEW", 0),
        "offer_sent_count": counts.get("OFFER_SENT", 0),
        "offers_sent": offers_sent,
        "offers_accepted": offers_accepted,
        "avg_ai_score": None if average is None else Decimal(str(average)).quantize(Decimal("0.1")),
        "updated_at": occurred,
    }
    existing = session.execute(
        sa.select(rm_agent_kpis.c.institution_id).where(rm_agent_kpis.c.institution_id == institution_id)
    ).first()
    if existing is None:
        session.execute(sa.insert(rm_agent_kpis).values(institution_id=institution_id, **values))
    else:
        session.execute(
            sa.update(rm_agent_kpis).where(rm_agent_kpis.c.institution_id == institution_id).values(**values)
        )


def _set_status(session: Session, request_id: UUID, status: str, occurred: datetime) -> None:
    session.execute(
        sa.update(rm_leads)
        .where(rm_leads.c.request_id == request_id)
        .values(status=status, updated_at=occurred)
    )


def _institutions(session: Session, product_ids: list[UUID]) -> list[UUID]:
    if not product_ids:
        return []
    rows = session.execute(
        sa.select(rm_products.c.institution_id).where(rm_products.c.product_id.in_(product_ids))
    ).scalars()
    return list(dict.fromkeys(rows))


def _product_ids(items) -> list[UUID]:
    found = []
    for item in items or []:
        if isinstance(item, dict) and item.get("product_id"):
            found.append(UUID(str(item["product_id"])))
    return found


def _latest_assessment(session: Session, request_id: UUID):
    return session.execute(
        sa.select(rm_assessments)
        .where(rm_assessments.c.request_id == request_id)
        .order_by(rm_assessments.c.attempt.desc())
    ).mappings().first()


def _request(session: Session, request_id: UUID):
    return session.execute(
        sa.select(rm_requests).where(rm_requests.c.request_id == request_id)
    ).mappings().first()


def _offer(session: Session, offer_id: UUID):
    return session.execute(sa.select(rm_offers).where(rm_offers.c.offer_id == offer_id)).mappings().first()


def _name(session: Session, user_id, fallback: str) -> str:
    if not user_id:
        return fallback
    name = session.execute(
        sa.select(rm_users.c.full_name).where(rm_users.c.user_id == UUID(str(user_id)))
    ).scalar_one_or_none()
    return name or fallback


def _lead_institutions(session: Session, request_id: UUID) -> set[UUID]:
    return set(session.execute(
        sa.select(rm_leads.c.institution_id).where(rm_leads.c.request_id == request_id)
    ).scalars())


def _timeline(session: Session, event: Event, text: str, actor: str) -> None:
    position = session.execute(
        sa.select(event_store.c.global_position).where(event_store.c.event_id == event.event_id)
    ).scalar_one()
    session.execute(
        sa.insert(rm_request_timeline).values(
            request_id=event.aggregate_id,
            global_position=position,
            event_type=event.event_type,
            actor=actor[:100],
            display_text=text[:300],
            occurred_at=to_naive_utc(event.occurred_at),
        )
    )
