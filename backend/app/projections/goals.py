"""GoalCreated, GoalUpdated ו-GoalArchived אל rm_goals."""

from uuid import UUID

import sqlalchemy as sa
from goalvest_core import Event
from sqlalchemy.orm import Session

from app.infrastructure.serialization import to_naive_utc
from app.infrastructure.tables import rm_goals
from app.projections.values import as_date, as_json, as_money

_COLUMNS = {
    "type": lambda value: value,
    "title": lambda value: value,
    "initial_amount": as_money,
    "monthly_deposit": as_money,
    "target_amount": as_money,
    "target_date": as_date,
    "flexibility": lambda value: value,
    "liquidity_need": lambda value: value,
    "excluded_channels": as_json,
    "preferred_channels": as_json,
    "preferred_institutions": as_json,
}


def project_goal_created(event: Event, session: Session) -> None:
    payload = event.payload
    session.execute(
        sa.insert(rm_goals).values(
            goal_id=event.aggregate_id,
            investor_id=UUID(str(payload["investor_id"])),
            active_request_id=None,
            status="ACTIVE",
            updated_at=to_naive_utc(event.occurred_at),
            **{column: cast(payload[column]) for column, cast in _COLUMNS.items()},
        )
    )


def project_goal_updated(event: Event, session: Session) -> None:
    changes = {column: cast(event.payload[column]) for column, cast in _COLUMNS.items() if column in event.payload}
    changes["updated_at"] = to_naive_utc(event.occurred_at)
    session.execute(sa.update(rm_goals).where(rm_goals.c.goal_id == event.aggregate_id).values(**changes))


def project_goal_archived(event: Event, session: Session) -> None:
    session.execute(
        sa.update(rm_goals)
        .where(rm_goals.c.goal_id == event.aggregate_id)
        .values(status="ARCHIVED", updated_at=to_naive_utc(event.occurred_at))
    )
