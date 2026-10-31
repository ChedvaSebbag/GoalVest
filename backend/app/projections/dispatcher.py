"""מריץ projectors באותה טרנזקציה שבה נכתב האירוע. ראו docs/06 §6.5 ו-docs/07 §7.4."""

# Read-model projections. A projector is a pure function (event, session) that updates an rm_*
# table, e.g. OfferSent -> rm_requests.status and a row in rm_notifications. No network or email
# calls here (side effects belong to workers). Read models can be rebuilt by replaying all events.

from collections.abc import Callable, Sequence

from goalvest_core import Event
from sqlalchemy.orm import Session

Projector = Callable[[Event, Session], None]


class ProjectionDispatcher:
    def __init__(self) -> None:
        self._projectors: dict[str, list[Projector]] = {}

    def register(self, event_type: str, projector: Projector) -> None:
        self._projectors.setdefault(event_type, []).append(projector)

    def dispatch(self, events: Sequence[Event], session: Session) -> None:
        for event in events:
            for projector in self._projectors.get(event.event_type, []):
                projector(event, session)
