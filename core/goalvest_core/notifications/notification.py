"""סימון התראה כנקראה. יצירת השורה היא השלכה של OfferSent."""

from uuid import UUID

from goalvest_core.aggregate import AggregateRoot
from goalvest_core.event import Event


class Notification(AggregateRoot):
    aggregate_type = "Notification"

    def __init__(self, aggregate_id: UUID | None = None) -> None:
        super().__init__(aggregate_id)
        self.is_read = False
        self.user_id: UUID | None = None

    def mark_read(self, *, user_id: UUID, metadata: dict | None = None) -> None:
        if self.is_read:
            return
        self._record("NotificationRead", {"user_id": str(user_id)}, metadata)

    def _when(self, event: Event) -> None:
        if event.event_type != "NotificationRead":
            raise NotImplementedError(f"Notification אינו מטפל ב-{event.event_type}")
        self.user_id = UUID(event.payload["user_id"])
        self.is_read = True
