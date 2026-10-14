"""טעינה ושמירה משותפת ל-handlers. אין כאן חוק עסקי."""

from typing import TypeVar
from uuid import UUID

from goalvest_core import NotFound
from goalvest_core.aggregate import AggregateRoot

from app.commands.bus import CommandContext

T = TypeVar("T", bound=AggregateRoot)


def load_typed(ctx: CommandContext, cls: type[T], aggregate_id: UUID) -> T:
    events = ctx.repository.load(aggregate_id, cls.aggregate_type)
    if not events:
        raise NotFound()
    return cls.from_events(events)


def metadata_for(command, user_id: UUID) -> dict:
    return {
        "user_id": str(user_id),
        "role": "INVESTOR",
        "correlation_id": command.correlation_id,
        "command_id": str(command.command_id),
    }


def save(ctx: CommandContext, aggregate: AggregateRoot, previous: int) -> None:
    if aggregate.uncommitted_events:
        ctx.repository.append(aggregate.aggregate_id, previous, aggregate.uncommitted_events)
