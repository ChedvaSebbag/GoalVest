"""חיבור הפקודה, ה-projector וה-bus לבקשה."""

from sqlalchemy.orm import Session

from app.commands.bus import CommandBus
from app.commands.goals import (
    ArchiveGoal,
    CreateGoal,
    UpdateGoal,
    handle_archive_goal,
    handle_create_goal,
    handle_update_goal,
)
from app.commands.investor_profile import (
    AssessRiskProfile,
    CreateInvestorProfile,
    handle_assess_risk,
    handle_create_profile,
)
from app.commands.register_user import RegisterUser, handle_register_user
from app.commands.requests import (
    CancelInvestmentRequest,
    SubmitInvestmentRequest,
    handle_cancel_request,
    handle_submit_request,
)
from app.projections.dispatcher import ProjectionDispatcher
from app.projections.goals import project_goal_archived, project_goal_created, project_goal_updated
from app.projections.investor_profiles import project_profile_created, project_risk_assessed
from app.projections.requests import project_request_cancelled, project_request_submitted
from app.projections.users import project_user_registered


def build_dispatcher() -> ProjectionDispatcher:
    dispatcher = ProjectionDispatcher()
    dispatcher.register("UserRegistered", project_user_registered)
    dispatcher.register("InvestorProfileCreated", project_profile_created)
    dispatcher.register("RiskProfileAssessed", project_risk_assessed)
    dispatcher.register("GoalCreated", project_goal_created)
    dispatcher.register("GoalUpdated", project_goal_updated)
    dispatcher.register("GoalArchived", project_goal_archived)
    dispatcher.register("InvestmentRequestSubmitted", project_request_submitted)
    dispatcher.register("RequestCancelled", project_request_cancelled)
    return dispatcher


def build_command_bus(session: Session, dispatcher: ProjectionDispatcher) -> CommandBus:
    bus = CommandBus(session, dispatcher)
    bus.register(RegisterUser, handle_register_user)
    bus.register(CreateInvestorProfile, handle_create_profile)
    bus.register(AssessRiskProfile, handle_assess_risk)
    bus.register(CreateGoal, handle_create_goal)
    bus.register(UpdateGoal, handle_update_goal)
    bus.register(ArchiveGoal, handle_archive_goal)
    bus.register(SubmitInvestmentRequest, handle_submit_request)
    bus.register(CancelInvestmentRequest, handle_cancel_request)
    return bus
