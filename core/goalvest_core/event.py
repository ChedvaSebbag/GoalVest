"""אירוע בלתי ניתן לשינוי. ראו docs/07 §7.2."""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any
from uuid import UUID


@dataclass(frozen=True)
class Event:
    event_id: UUID
    aggregate_id: UUID
    version: int
    event_type: str
    aggregate_type: str
    payload: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)
    schema_version: int = 1
    occurred_at: datetime = field(default_factory=lambda: datetime.now(UTC))
