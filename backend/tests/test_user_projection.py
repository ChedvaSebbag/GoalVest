"""UserRegistered נכתב ל-rm_users, כולל סטטוס ACTIVE."""

from uuid import uuid4

import sqlalchemy as sa
from app.infrastructure.tables import rm_users
from app.projections.users import project_user_registered
from goalvest_core import Event


def test_projects_investor_without_institution(session):
    user_id = uuid4()
    project_user_registered(_event(user_id, institution_id=None), session)
    session.commit()
    row = session.execute(sa.select(rm_users)).mappings().one()
    assert row["user_id"] == user_id
    assert row["email"] == "noa@mail.com"
    assert row["role"] == "INVESTOR"
    assert row["institution_id"] is None
    assert row["status"] == "ACTIVE"
    assert row["password_hash"] == "hashed"


def test_projects_agent_institution(session):
    user_id = uuid4()
    institution_id = uuid4()
    project_user_registered(_event(user_id, role="AGENT", institution_id=str(institution_id)), session)
    session.commit()
    row = session.execute(sa.select(rm_users)).mappings().one()
    assert row["role"] == "AGENT"
    assert row["institution_id"] == institution_id


def _event(user_id, role="INVESTOR", institution_id=None) -> Event:
    return Event(
        event_id=uuid4(),
        aggregate_id=user_id,
        version=1,
        event_type="UserRegistered",
        aggregate_type="UserAccount",
        payload={
            "email": "noa@mail.com",
            "full_name": "נועה לוי",
            "phone": "0501234567",
            "role": role,
            "password_hash": "hashed",
            "institution_id": institution_id,
            "license_no": "LIC-1" if role == "AGENT" else None,
        },
    )
