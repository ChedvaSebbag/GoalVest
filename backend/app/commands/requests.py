"""הגשת בקשה וביטול. בקשה פעילה אחת ליעד, ורק אחרי שאלון סיכון."""

# Handler flow (submit): load the goal and check ownership (404 otherwise) -> check rules
# (active goal, risk profile present, no active request) -> InvestmentRequest.submit() records
# InvestmentRequestSubmitted with a snapshot of the goal -> save() appends to the event store
# (projections run in the same transaction) -> return {id, version}.

from dataclasses import dataclass
from uuid import UUID

from goalvest_core import BusinessRuleViolation, NotFound
from goalvest_core.requests import InvestmentRequest

from app.commands.bus import Command, CommandContext, CommandResult
from app.commands.goals import _owned, _scored_profile, _snapshot
from app.commands.loading import load_typed, metadata_for, save
from app.queries.goals import find_active_request
from app.queries.requests import get_request_row


@dataclass(frozen=True)
class SubmitInvestmentRequest(Command):
    actor_id: UUID
    goal_id: UUID
    consent_share_contact: bool
    correlation_id: str | None = None


@dataclass(frozen=True)
class CancelInvestmentRequest(Command):
    actor_id: UUID
    request_id: UUID
    reason: str = ""
    correlation_id: str | None = None


def handle_submit_request(command: SubmitInvestmentRequest, ctx: CommandContext) -> CommandResult:
    goal = _owned(ctx, command.goal_id, command.actor_id)
    if goal.status != "ACTIVE":
        raise BusinessRuleViolation("היעד בארכיון", code="GOAL_ARCHIVED")
    profile = _scored_profile(ctx, command.actor_id)
    active = find_active_request(ctx.repository.session, goal.aggregate_id)
    goal.ensure_no_active_request(active["request_id"] if active is not None else None)
    request = InvestmentRequest()
    request.submit(
        goal_id=goal.aggregate_id,
        investor_id=command.actor_id,
        snapshot=_snapshot(goal, profile),
        consent_share_contact=command.consent_share_contact,
        metadata=metadata_for(command, command.actor_id),
    )
    save(ctx, request, 0)
    return CommandResult(id=request.aggregate_id, version=request.version)


def handle_cancel_request(command: CancelInvestmentRequest, ctx: CommandContext) -> CommandResult:
    request = load_typed(ctx, InvestmentRequest, command.request_id)
    if request.investor_id != command.actor_id:
        raise NotFound()
    row = get_request_row(ctx.repository.session, command.request_id)
    if row is None:
        raise NotFound()
    request.use_projected_status(row["status"])
    previous = request.version
    request.cancel(
        by=str(command.actor_id),
        reason=command.reason,
        metadata=metadata_for(command, command.actor_id),
    )
    save(ctx, request, previous)
    return CommandResult(id=request.aggregate_id, version=request.version)
