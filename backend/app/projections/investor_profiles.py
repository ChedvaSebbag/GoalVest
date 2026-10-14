"""InvestorProfileCreated ו-RiskProfileAssessed אל rm_investor_profiles."""

import sqlalchemy as sa
from goalvest_core import Event
from sqlalchemy.orm import Session

from app.infrastructure.serialization import to_naive_utc
from app.infrastructure.tables import rm_investor_profiles
from app.projections.values import as_json


def project_profile_created(event: Event, session: Session) -> None:
    payload = event.payload
    session.execute(
        sa.insert(rm_investor_profiles).values(
            user_id=event.aggregate_id,
            birth_year=payload["birth_year"],
            marital_status=payload["marital_status"],
            monthly_income_range=payload["monthly_income_range"],
            has_emergency_fund=bool(payload["has_emergency_fund"]),
            existing_products=as_json(payload["existing_products"]),
            risk_score=None,
            risk_label=None,
            answers=None,
            assessed_at=None,
        )
    )


def project_risk_assessed(event: Event, session: Session) -> None:
    payload = event.payload
    answers = payload["answers"]
    session.execute(
        sa.update(rm_investor_profiles)
        .where(rm_investor_profiles.c.user_id == event.aggregate_id)
        .values(
            birth_year=answers["birth_year"],
            marital_status=answers["marital_status"],
            monthly_income_range=answers["monthly_income_range"],
            has_emergency_fund=answers["emergency_fund"] != "NONE",
            existing_products=as_json(answers["existing_products"]),
            risk_score=payload["score"],
            risk_label=payload["label"],
            answers=as_json(answers),
            assessed_at=to_naive_utc(event.occurred_at),
        )
    )
