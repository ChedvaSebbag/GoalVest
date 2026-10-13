"""ה-projector רץ בטרנזקציה של append, ולא נשאר אחרי כישלון."""

from uuid import uuid4

import pytest
import sqlalchemy as sa
from app.infrastructure.event_store import EventStoreRepository
from app.projections.dispatcher import ProjectionDispatcher
from goalvest_core import Event

probe = sa.Table(
    "test_projection_probe",
    sa.MetaData(),
    sa.Column("probe_id", sa.Integer, primary_key=True, autoincrement=True),
    sa.Column("event_id", sa.Uuid, nullable=False),
)


def _opened(aggregate_id) -> Event:
    return Event(
        event_id=uuid4(),
        aggregate_id=aggregate_id,
        version=1,
        event_type="AccountOpened",
        aggregate_type="Wallet",
    )


def _count(session) -> int:
    return session.scalar(sa.select(sa.func.count()).select_from(probe))


def test_projector_runs_in_the_append_transaction(session):
    probe.metadata.create_all(session.get_bind())
    dispatcher = ProjectionDispatcher()
    dispatcher.register(
        "AccountOpened",
        lambda event, db: db.execute(sa.insert(probe).values(event_id=event.event_id)),
    )
    repo = EventStoreRepository(session, dispatcher)
    aggregate_id = uuid4()

    repo.append(aggregate_id, 0, [_opened(aggregate_id)])

    assert _count(session) == 1
    assert len(repo.load(aggregate_id)) == 1
    session.rollback()
    assert _count(session) == 0
    assert repo.load(aggregate_id) == []


def test_projector_failure_does_not_keep_the_event_or_the_read_row(session):
    probe.metadata.create_all(session.get_bind())
    dispatcher = ProjectionDispatcher()

    def project(event: Event, db) -> None:
        db.execute(sa.insert(probe).values(event_id=event.event_id))
        raise RuntimeError("כשל בהטלה")

    dispatcher.register("AccountOpened", project)
    repo = EventStoreRepository(session, dispatcher)
    aggregate_id = uuid4()

    with pytest.raises(RuntimeError, match="כשל בהטלה"):
        repo.append(aggregate_id, 0, [_opened(aggregate_id)])

    assert _count(session) == 0
    assert repo.load(aggregate_id) == []
