"""קבלה ודחייה של הצעה על ידי המשקיע."""

from dataclasses import dataclass
from uuid import UUID

from goalvest_core import NotFound
from goalvest_core.requests import InvestmentRequest

from app.commands.bus import Command, CommandContext, CommandResult
from app.commands.loading import load_typed, save
from app.queries.offers import offer_row


@dataclass(frozen=True)
class AcceptOffer(Command):
    actor_id: UUID
    offer_id: UUID
    correlation_id: str | None = None


@dataclass(frozen=True)
class DeclineOffer(Command):
    actor_id: UUID
    offer_id: UUID
    reason: str = ""
    correlation_id: str | None = None


def handle_accept_offer(command: AcceptOffer, ctx: CommandContext) -> CommandResult:
    request, previous = _owned(ctx, command)
    request.accept_offer(offer_id=command.offer_id, metadata=_meta(command))
    save(ctx, request, previous)
    return CommandResult(id=command.offer_id, version=request.version)


def handle_decline_offer(command: DeclineOffer, ctx: CommandContext) -> CommandResult:
    request, previous = _owned(ctx, command)
    request.decline_offer(offer_id=command.offer_id, reason=command.reason, metadata=_meta(command))
    save(ctx, request, previous)
    return CommandResult(id=command.offer_id, version=request.version)


def _owned(ctx: CommandContext, command: AcceptOffer | DeclineOffer) -> tuple[InvestmentRequest, int]:
    row = offer_row(ctx.repository.session, command.offer_id)
    if row is None or row["investor_id"] != command.actor_id:
        raise NotFound()
    request = load_typed(ctx, InvestmentRequest, row["request_id"])
    if request.investor_id != command.actor_id:
        raise NotFound()
    return request, request.version


def _meta(command: Command) -> dict:
    return {
        "user_id": str(command.actor_id),
        "role": "INVESTOR",
        "correlation_id": command.correlation_id,
        "command_id": str(command.command_id),
    }
