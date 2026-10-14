"""פקודות הסוכן: התחלת הערכה, השלמה, כישלון ושחרור נעילה. אין כאן חישוב."""

from dataclasses import dataclass
from uuid import UUID

from goalvest_core import ConcurrencyError
from goalvest_core.requests import InvestmentRequest

from app.commands.bus import Command, CommandContext, CommandResult
from app.commands.loading import load_typed, save


@dataclass(frozen=True)
class StartAssessment(Command):
    request_id: UUID
    expected_version: int
    agent_run_id: UUID
    model: str


@dataclass(frozen=True)
class CompleteAssessment(Command):
    request_id: UUID
    expected_version: int
    assessment: dict


@dataclass(frozen=True)
class FailAssessment(Command):
    request_id: UUID
    expected_version: int
    error_code: str
    message: str
    retry_at: str


@dataclass(frozen=True)
class AbortAssessment(Command):
    request_id: UUID
    expected_version: int
    reason: str


def handle_start_assessment(command: StartAssessment, ctx: CommandContext) -> CommandResult:
    request = _at_version(ctx, command.request_id, command.expected_version)
    request.start_assessment(agent_run_id=command.agent_run_id, model=command.model, metadata=_meta(command))
    save(ctx, request, command.expected_version)
    return CommandResult(id=request.aggregate_id, version=request.version)


def handle_complete_assessment(command: CompleteAssessment, ctx: CommandContext) -> CommandResult:
    request = _at_version(ctx, command.request_id, command.expected_version)
    request.complete_assessment(command.assessment, metadata=_meta(command))
    save(ctx, request, command.expected_version)
    return CommandResult(id=request.aggregate_id, version=request.version)


def handle_fail_assessment(command: FailAssessment, ctx: CommandContext) -> CommandResult:
    request = _at_version(ctx, command.request_id, command.expected_version)
    request.fail_assessment(
        error_code=command.error_code,
        message=command.message,
        retry_at=command.retry_at,
        metadata=_meta(command),
    )
    save(ctx, request, command.expected_version)
    return CommandResult(id=request.aggregate_id, version=request.version)


def handle_abort_assessment(command: AbortAssessment, ctx: CommandContext) -> CommandResult:
    request = _at_version(ctx, command.request_id, command.expected_version)
    request.abort_assessment(reason=command.reason, metadata=_meta(command))
    save(ctx, request, command.expected_version)
    return CommandResult(id=request.aggregate_id, version=request.version)


def _at_version(ctx: CommandContext, request_id: UUID, expected_version: int) -> InvestmentRequest:
    request = load_typed(ctx, InvestmentRequest, request_id)
    if request.version != expected_version:
        raise ConcurrencyError(request_id, expected_version)
    return request


def _meta(command: Command) -> dict:
    return {"command_id": str(command.command_id)}
