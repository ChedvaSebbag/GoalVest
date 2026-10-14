"""EventStoreRepository – append ו-load. כתיבה ל-EventStore היא INSERT בלבד. ראו docs/07 §7.2."""

from collections.abc import Sequence
from uuid import UUID

import sqlalchemy as sa
from goalvest_core import ConcurrencyError, Event
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.infrastructure.serialization import dumps, loads, to_aware_utc, to_naive_utc
from app.infrastructure.tables import event_store
from app.projections.dispatcher import ProjectionDispatcher


class EventStoreRepository:
    def __init__(self, session: Session, dispatcher: ProjectionDispatcher | None = None) -> None:
        self._session = session
        self._dispatcher = dispatcher if dispatcher is not None else ProjectionDispatcher()

    @property
    def session(self) -> Session:
        return self._session

    def append(self, aggregate_id: UUID, expected_version: int, events: Sequence[Event]) -> None:
        """כותב אירועים ומריץ projectors באותה טרנזקציה. ה-commit נשאר אצל הקורא.

        כישלון (גרסה כפולה או projector) מבטל את הטרנזקציה, כדי שלא יישאר כתיבה חלקית.
        """
        pending = list(events)
        if not pending:
            raise ValueError("append דורש לפחות אירוע אחד")
        self._validate(aggregate_id, expected_version, pending)
        try:
            for event in pending:
                self._session.execute(
                    sa.insert(event_store).values(
                        event_id=event.event_id,
                        aggregate_type=event.aggregate_type,
                        aggregate_id=event.aggregate_id,
                        version=event.version,
                        event_type=event.event_type,
                        schema_version=event.schema_version,
                        payload=dumps(event.payload),
                        metadata=dumps(event.metadata),
                        occurred_at=to_naive_utc(event.occurred_at),
                    )
                )
            self._session.flush()
            self._dispatcher.dispatch(pending, self._session)
        except IntegrityError as exc:
            self._session.rollback()
            if _is_version_conflict(exc):
                raise ConcurrencyError(aggregate_id, expected_version) from exc
            raise
        except Exception:
            self._session.rollback()
            raise

    def load(self, aggregate_id: UUID, aggregate_type: str | None = None) -> list[Event]:
        query = sa.select(event_store).where(event_store.c.aggregate_id == aggregate_id)
        if aggregate_type is not None:
            query = query.where(event_store.c.aggregate_type == aggregate_type)
        rows = self._session.execute(query.order_by(event_store.c.version)).mappings()
        return [_to_event(row) for row in rows]

    @staticmethod
    def _validate(aggregate_id: UUID, expected_version: int, events: Sequence[Event]) -> None:
        for offset, event in enumerate(events, start=1):
            if event.aggregate_id != aggregate_id:
                raise ValueError("aggregate_id של האירוע אינו תואם ל-append")
            if event.version != expected_version + offset:
                raise ValueError(
                    f"גרסת האירוע {event.version} אינה expected_version + {offset}"
                )


def _to_event(row: sa.RowMapping) -> Event:
    payload = loads(row["payload"])
    metadata = loads(row["metadata"])
    if not isinstance(payload, dict) or not isinstance(metadata, dict):
        raise TypeError("payload ו-metadata חייבים להיות אובייקטי JSON")
    return Event(
        event_id=row["event_id"],
        aggregate_id=row["aggregate_id"],
        version=row["version"],
        event_type=row["event_type"],
        aggregate_type=row["aggregate_type"],
        payload=payload,
        metadata=metadata,
        schema_version=row["schema_version"],
        occurred_at=to_aware_utc(row["occurred_at"]),
    )


def _is_version_conflict(exc: IntegrityError) -> bool:
    message = str(exc.orig).lower()
    if "uq_aggregate_version" in message:
        return True
    return "aggregate_id" in message and "version" in message
