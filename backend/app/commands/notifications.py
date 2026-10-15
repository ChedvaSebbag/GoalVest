"""סימון התראה כנקראה."""

from dataclasses import dataclass
from uuid import UUID

from goalvest_core import NotFound
from goalvest_core.notifications import Notification

from app.commands.bus import Command, CommandContext, CommandResult
from app.commands.loading import save
from app.queries.notifications import notification_row


@dataclass(frozen=True)
class MarkNotificationRead(Command):
    actor_id: UUID
    notification_id: UUID
    correlation_id: str | None = None


def handle_mark_read(command: MarkNotificationRead, ctx: CommandContext) -> CommandResult:
    row = notification_row(ctx.repository.session, command.notification_id)
    if row is None or row["user_id"] != command.actor_id:
        raise NotFound()
    events = ctx.repository.load(command.notification_id, Notification.aggregate_type)
    note = Notification.from_events(events) if events else Notification(command.notification_id)
    if note.is_read or row["is_read"]:
        return CommandResult(id=command.notification_id, version=note.version)
    previous = note.version
    note.mark_read(
        user_id=command.actor_id,
        metadata={
            "user_id": str(command.actor_id),
            "correlation_id": command.correlation_id,
            "command_id": str(command.command_id),
        },
    )
    save(ctx, note, previous)
    return CommandResult(id=command.notification_id, version=note.version)
