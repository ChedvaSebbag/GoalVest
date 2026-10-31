"""AggregateRoot – שחזור מצב מאירועים ורישום אירועים חדשים. ראו docs/06 §6.5."""

# Aggregate root (Event Sourcing).
# State is never stored directly: it is rebuilt by replaying the aggregate's events in order
# (from_events -> apply -> _when). _when only mutates fields; business rules live in the
# subclasses' command methods. _record creates a new event with version + 1, applies it and
# keeps it as uncommitted until the repository appends it. `version` drives optimistic concurrency.

from collections.abc import Sequence
from typing import ClassVar, Self
from uuid import UUID, uuid4

from goalvest_core.event import Event


class AggregateRoot:
    aggregate_type: ClassVar[str] = ""

    def __init__(self, aggregate_id: UUID | None = None) -> None:
        self.aggregate_id = aggregate_id if aggregate_id is not None else uuid4()
        self.version = 0
        self._uncommitted: list[Event] = []

    @classmethod
    def from_events(cls, events: Sequence[Event]) -> Self:
        """בונה את המצב מחדש. האירועים ההיסטוריים אינם נחשבים לאירועים חדשים."""
        if not events:
            raise ValueError("שחזור אגרגט דורש לפחות אירוע אחד")
        aggregate_id = events[0].aggregate_id
        aggregate = cls(aggregate_id)
        for event in events:
            aggregate.apply(event)
        aggregate._uncommitted.clear()
        return aggregate

    def apply(self, event: Event) -> None:
        if event.aggregate_id != self.aggregate_id:
            raise ValueError("האירוע שייך לאגרגט אחר")
        if event.version != self.version + 1:
            raise ValueError(
                f"גרסת האירוע {event.version} אינה המשך של {self.version}"
            )
        self._when(event)
        self.version = event.version

    def _when(self, event: Event) -> None:
        """עדכון מצב בלבד, בלי בדיקת חוקים. כל Aggregate מממש את זה."""
        raise NotImplementedError(f"{type(self).__name__} אינו מטפל ב-{event.event_type}")

    def _record(
        self,
        event_type: str,
        payload: dict | None = None,
        metadata: dict | None = None,
    ) -> Event:
        if not type(self).aggregate_type:
            raise RuntimeError(f"{type(self).__name__} חייב להגדיר aggregate_type")
        event = Event(
            event_id=uuid4(),
            aggregate_id=self.aggregate_id,
            version=self.version + 1,
            event_type=event_type,
            aggregate_type=type(self).aggregate_type,
            payload=dict(payload or {}),
            metadata=dict(metadata or {}),
        )
        self.apply(event)
        self._uncommitted.append(event)
        return event

    @property
    def uncommitted_events(self) -> tuple[Event, ...]:
        return tuple(self._uncommitted)
