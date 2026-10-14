"""חיבור הפקודה, ה-projector וה-bus לבקשה."""

from sqlalchemy.orm import Session

from app.commands.assessments import (
    AbortAssessment,
    CompleteAssessment,
    FailAssessment,
    StartAssessment,
    handle_abort_assessment,
    handle_complete_assessment,
    handle_fail_assessment,
    handle_start_assessment,
)
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
from app.commands.products import (
    CreateProduct,
    DeactivateProduct,
    UpdateProduct,
    UploadProductDocument,
    handle_create_product,
    handle_deactivate_product,
    handle_update_product,
    handle_upload_document,
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
from app.projections.products import (
    project_document_index_failed,
    project_document_indexed,
    project_document_uploaded,
    project_product_created,
    project_product_deactivated,
    project_product_updated,
)
from app.projections.requests import (
    project_assessment_aborted,
    project_assessment_completed,
    project_assessment_failed,
    project_assessment_started,
    project_request_cancelled,
    project_request_submitted,
)
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
    dispatcher.register("AssessmentStarted", project_assessment_started)
    dispatcher.register("AIAssessmentCompleted", project_assessment_completed)
    dispatcher.register("AIAssessmentFailed", project_assessment_failed)
    dispatcher.register("AssessmentAborted", project_assessment_aborted)
    dispatcher.register("ProductCreated", project_product_created)
    dispatcher.register("ProductUpdated", project_product_updated)
    dispatcher.register("ProductDeactivated", project_product_deactivated)
    dispatcher.register("ProductDocumentUploaded", project_document_uploaded)
    dispatcher.register("ProductDocumentIndexed", project_document_indexed)
    dispatcher.register("ProductDocumentIndexFailed", project_document_index_failed)
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
    bus.register(StartAssessment, handle_start_assessment)
    bus.register(CompleteAssessment, handle_complete_assessment)
    bus.register(FailAssessment, handle_fail_assessment)
    bus.register(AbortAssessment, handle_abort_assessment)
    bus.register(CreateProduct, handle_create_product)
    bus.register(UpdateProduct, handle_update_product)
    bus.register(DeactivateProduct, handle_deactivate_product)
    bus.register(UploadProductDocument, handle_upload_document)
    return bus
