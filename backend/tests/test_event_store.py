"""append, load, ו-ConcurrencyError על SQLite בזיכרון."""

import re
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from uuid import UUID, uuid4

import pytest
import sqlalchemy as sa
from app.infrastructure.event_store import EventStoreRepository
from app.infrastructure.tables import event_store, processed_commands
from goalvest_core import ConcurrencyError, Event


def _event(aggregate_id, version, **payload) -> Event:
    return Event(
        event_id=uuid4(),
        aggregate_id=aggregate_id,
        version=version,
        event_type="MoneyDeposited",
        aggregate_type="Wallet",
        payload=payload,
        occurred_at=datetime(2026, 10, 13, 17, 45, 1, 123000, tzinfo=UTC),
    )


def test_append_then_load_returns_the_same_stream(session):
    aggregate_id = uuid4()
    first = _event(aggregate_id, 1, amount=Decimal("1.00"))
    second = _event(aggregate_id, 2, amount=Decimal("2.00"))
    repo = EventStoreRepository(session)

    repo.append(aggregate_id, 0, [first, second])
    session.commit()

    loaded = repo.load(aggregate_id)
    assert loaded == [first, second]


def test_decimal_and_uuid_round_trip_without_loss(session):
    aggregate_id = uuid4()
    product_id = uuid4()
    user_id = uuid4()
    noted_at = datetime(2026, 10, 13, 12, 0, tzinfo=UTC)
    event = Event(
        event_id=uuid4(),
        aggregate_id=aggregate_id,
        version=1,
        event_type="MoneyDeposited",
        aggregate_type="Wallet",
        payload={"amount": Decimal("1234.56"), "product_id": product_id, "note": "סכום"},
        metadata={"user_id": user_id, "at": noted_at},
        occurred_at=datetime(2026, 10, 13, 17, 45, 1, 123000, tzinfo=UTC),
    )
    repo = EventStoreRepository(session)
    repo.append(aggregate_id, 0, [event])
    session.commit()

    raw_payload = session.execute(sa.select(event_store.c.payload)).scalar_one()
    assert "1234.56" in raw_payload
    assert "סכום" in raw_payload
    assert "\\u05e1" not in raw_payload

    loaded = repo.load(aggregate_id)[0]
    assert loaded.payload["amount"] == Decimal("1234.56")
    assert isinstance(loaded.payload["amount"], Decimal)
    assert loaded.payload["product_id"] == product_id
    assert isinstance(loaded.payload["product_id"], UUID)
    assert loaded.payload["note"] == "סכום"
    assert loaded.metadata["user_id"] == user_id
    assert isinstance(loaded.metadata["user_id"], UUID)
    assert loaded.metadata["at"] == noted_at
    assert loaded.occurred_at == event.occurred_at


def test_duplicate_version_raises_concurrency_error(session):
    aggregate_id = uuid4()
    repo = EventStoreRepository(session)
    repo.append(aggregate_id, 0, [_event(aggregate_id, 1, amount=Decimal(1))])
    session.commit()

    with pytest.raises(ConcurrencyError) as caught:
        repo.append(aggregate_id, 0, [_event(aggregate_id, 1, amount=Decimal(9))])

    assert caught.value.aggregate_id == aggregate_id
    assert caught.value.expected_version == 0
    loaded = repo.load(aggregate_id)
    assert len(loaded) == 1
    assert loaded[0].payload["amount"] == Decimal(1)


def test_tables_match_migration_columns():
    assert [column.name for column in event_store.columns] == [
        "global_position",
        "event_id",
        "aggregate_type",
        "aggregate_id",
        "version",
        "event_type",
        "schema_version",
        "payload",
        "metadata",
        "occurred_at",
    ]
    assert [column.name for column in processed_commands.columns] == [
        "command_id",
        "result_json",
        "processed_at",
    ]
    assert "UQ_Aggregate_Version" in {constraint.name for constraint in event_store.constraints}
    assert "IX_EventStore_Type" in {index.name for index in event_store.indexes}


def test_event_store_source_has_no_update_or_delete():
    root = Path(__file__).resolve().parents[1] / "app"
    pattern = re.compile(
        r"update\(\s*event_store|delete\(\s*event_store|UPDATE\s+EventStore|DELETE\s+FROM\s+EventStore",
        re.IGNORECASE,
    )
    offenders = [
        str(path)
        for path in root.rglob("*.py")
        if pattern.search(path.read_text(encoding="utf-8"))
    ]
    assert offenders == []
