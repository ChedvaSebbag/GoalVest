"""יצירה, עדכון וארכוב של יעד. עריכה עם בקשה פעילה מחליפה אותה (FR-15)."""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from uuid import UUID

from goalvest_core import BusinessRuleViolation, NotFound
from goalvest_core.goals import Goal
from goalvest_core.investor import InvestorProfile
from goalvest_core.requests import InvestmentRequest, RequestStatus

from app.commands.bus import Command, CommandContext, CommandResult
from app.commands.loading import load_typed, metadata_for, save
from app.queries.goals import find_active_request
from app.reference.institutions import INSTITUTIONS


@dataclass(frozen=True)
class GoalData:
    goal_type: str
    title: str
    initial_amount: Decimal
    monthly_deposit: Decimal
    target_amount: Decimal
    target_date: date
    flexibility: str
    liquidity_need: str
    excluded_channels: tuple[str, ...]
    preferred_channels: tuple[str, ...]
    preferred_institutions: tuple[str, ...]

    def as_kwargs(self) -> dict:
        return {
            "goal_type": self.goal_type,
            "title": self.title,
            "initial_amount": self.initial_amount,
            "monthly_deposit": self.monthly_deposit,
            "target_amount": self.target_amount,
            "target_date": self.target_date,
            "flexibility": self.flexibility,
            "liquidity_need": self.liquidity_need,
            "excluded_channels": list(self.excluded_channels),
            "preferred_channels": list(self.preferred_channels),
            "preferred_institutions": list(self.preferred_institutions),
        }


@dataclass(frozen=True)
class CreateGoal(Command):
    actor_id: UUID
    data: GoalData
    correlation_id: str | None = None


@dataclass(frozen=True)
class UpdateGoal(Command):
    actor_id: UUID
    goal_id: UUID
    data: GoalData
    consent_share_contact: bool = False
    correlation_id: str | None = None


@dataclass(frozen=True)
class ArchiveGoal(Command):
    actor_id: UUID
    goal_id: UUID
    reason: str = ""
    correlation_id: str | None = None


def handle_create_goal(command: CreateGoal, ctx: CommandContext) -> CommandResult:
    goal = Goal()
    goal.create(
        investor_id=command.actor_id,
        today=date.today(),
        known_institutions=_known(),
        metadata=metadata_for(command, command.actor_id),
        **command.data.as_kwargs(),
    )
    save(ctx, goal, 0)
    return CommandResult(id=goal.aggregate_id, version=goal.version)


def handle_update_goal(command: UpdateGoal, ctx: CommandContext) -> CommandResult:
    goal = _owned(ctx, command.goal_id, command.actor_id)
    active = find_active_request(ctx.repository.session, goal.aggregate_id)
    request = _active_request(ctx, active)
    previous = goal.version
    meta = metadata_for(command, command.actor_id)
    goal.update(
        today=date.today(),
        known_institutions=_known(),
        metadata=meta,
        **command.data.as_kwargs(),
    )
    changed = bool(goal.uncommitted_events)
    # בקשה שנכשלה מוגשת מחדש בכל שמירה, גם בלי שינוי בשדות היעד
    failed = request is not None and request.status is RequestStatus.FAILED
    resubmit = request is not None and (changed or failed)
    if resubmit and not command.consent_share_contact:
        raise BusinessRuleViolation("יש לאשר שיתוף פרטים עם סוכנים", code="CONSENT_REQUIRED")
    opening = resubmit or (request is None and command.consent_share_contact)
    profile = _scored_profile(ctx, command.actor_id) if opening else None
    save(ctx, goal, previous)
    if resubmit and profile is not None:
        request_previous = request.version
        request.cancel(by=str(command.actor_id), reason="GOAL_UPDATED", metadata=meta)
        save(ctx, request, request_previous)
        _submit(ctx, goal, profile, command.actor_id, meta)
    elif request is None and command.consent_share_contact and profile is not None:
        _submit(ctx, goal, profile, command.actor_id, meta)
    return CommandResult(id=goal.aggregate_id, version=goal.version)


def handle_archive_goal(command: ArchiveGoal, ctx: CommandContext) -> CommandResult:
    goal = _owned(ctx, command.goal_id, command.actor_id)
    active = find_active_request(ctx.repository.session, goal.aggregate_id)
    request = _active_request(ctx, active)
    previous = goal.version
    meta = metadata_for(command, command.actor_id)
    goal.archive(command.reason, meta)
    save(ctx, goal, previous)
    if request is not None:
        request_previous = request.version
        request.cancel(by=str(command.actor_id), reason="GOAL_ARCHIVED", metadata=meta)
        save(ctx, request, request_previous)
    return CommandResult(id=goal.aggregate_id, version=goal.version)


def _owned(ctx: CommandContext, goal_id: UUID, actor_id: UUID) -> Goal:
    goal = load_typed(ctx, Goal, goal_id)
    if goal.investor_id != actor_id:
        raise NotFound()
    return goal


def _active_request(ctx: CommandContext, active) -> InvestmentRequest | None:
    if active is None:
        return None
    request = load_typed(ctx, InvestmentRequest, active["request_id"])
    request.use_projected_status(active["status"])
    request.ensure_goal_change_allowed()
    return request


def _scored_profile(ctx: CommandContext, user_id: UUID) -> InvestorProfile:
    events = ctx.repository.load(user_id, InvestorProfile.aggregate_type)
    profile = InvestorProfile.from_events(events) if events else None
    if profile is None or profile.risk_score is None:
        raise BusinessRuleViolation(
            "יש להשלים שאלון סיכון לפני הגשת בקשה",
            code="RISK_PROFILE_REQUIRED",
        )
    return profile


def _submit(ctx: CommandContext, goal: Goal, profile: InvestorProfile, actor_id: UUID, meta: dict) -> None:
    request = InvestmentRequest()
    request.submit(
        goal_id=goal.aggregate_id,
        investor_id=actor_id,
        snapshot=_snapshot(goal, profile),
        consent_share_contact=True,
        metadata=meta,
    )
    save(ctx, request, 0)


def _snapshot(goal: Goal, profile: InvestorProfile) -> dict:
    return {
        "goal": {
            "type": goal.goal_type,
            "title": goal.title,
            "initial_amount": goal.initial_amount,
            "monthly_deposit": goal.monthly_deposit,
            "target_amount": goal.target_amount,
            "target_date": goal.target_date.isoformat(),
            "flexibility": goal.flexibility,
            "liquidity_need": goal.liquidity_need,
            "excluded_channels": list(goal.excluded_channels),
            "preferred_channels": list(goal.preferred_channels),
            "preferred_institutions": list(goal.preferred_institutions),
        },
        "risk": {
            "score": profile.risk_score,
            "label": profile.risk_label,
            "answers": profile.answers,
        },
    }


def _known() -> set[str]:
    return {str(item.id) for item in INSTITUTIONS}
