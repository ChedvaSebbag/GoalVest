"""יצירת פרופיל ושאלון סיכון. הציון מחושב ב-Aggregate."""

from dataclasses import dataclass
from datetime import date
from uuid import UUID

from goalvest_core.investor import InvestorProfile

from app.commands.bus import Command, CommandContext, CommandResult
from app.commands.loading import metadata_for, save


@dataclass(frozen=True)
class CreateInvestorProfile(Command):
    actor_id: UUID
    birth_year: int
    marital_status: str
    monthly_income_range: str
    has_emergency_fund: bool
    existing_products: tuple[str, ...]
    correlation_id: str | None = None


@dataclass(frozen=True)
class AssessRiskProfile(Command):
    actor_id: UUID
    answers: dict
    correlation_id: str | None = None


def handle_create_profile(command: CreateInvestorProfile, ctx: CommandContext) -> CommandResult:
    profile, previous = _open(ctx, command.actor_id)
    profile.create_profile(
        birth_year=command.birth_year,
        marital_status=command.marital_status,
        monthly_income_range=command.monthly_income_range,
        has_emergency_fund=command.has_emergency_fund,
        existing_products=list(command.existing_products),
        today=date.today(),
        metadata=metadata_for(command, command.actor_id),
    )
    save(ctx, profile, previous)
    return CommandResult(id=profile.aggregate_id, version=profile.version)


def handle_assess_risk(command: AssessRiskProfile, ctx: CommandContext) -> CommandResult:
    profile, previous = _open(ctx, command.actor_id)
    profile.record_assessment(
        command.answers,
        today=date.today(),
        metadata=metadata_for(command, command.actor_id),
    )
    save(ctx, profile, previous)
    return CommandResult(id=profile.aggregate_id, version=profile.version)


def _open(ctx: CommandContext, user_id: UUID) -> tuple[InvestorProfile, int]:
    events = ctx.repository.load(user_id, InvestorProfile.aggregate_type)
    if events:
        profile = InvestorProfile.from_events(events)
        return profile, profile.version
    return InvestorProfile(user_id), 0
