"""קריאה מ-rm_investor_profiles בלבד."""

from uuid import UUID

import sqlalchemy as sa
from sqlalchemy.orm import Session

from app.infrastructure.serialization import loads
from app.infrastructure.tables import rm_investor_profiles


def get_profile(session: Session, user_id: UUID) -> dict:
    row = session.execute(
        sa.select(rm_investor_profiles).where(rm_investor_profiles.c.user_id == user_id)
    ).mappings().first()
    if row is None:
        return {
            "birthYear": None,
            "maritalStatus": None,
            "monthlyIncomeRange": None,
            "hasEmergencyFund": None,
            "existingProducts": [],
            "riskScore": None,
            "riskLabel": None,
        }
    products = loads(row["existing_products"]) if row["existing_products"] else []
    return {
        "birthYear": row["birth_year"],
        "maritalStatus": row["marital_status"],
        "monthlyIncomeRange": row["monthly_income_range"],
        "hasEmergencyFund": row["has_emergency_fund"],
        "existingProducts": products,
        "riskScore": row["risk_score"],
        "riskLabel": row["risk_label"],
    }
