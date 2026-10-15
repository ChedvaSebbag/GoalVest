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
from app.commands.leads import (
    ApproveAssessment,
    ClaimLead,
    RejectAssessment,
    RequestReevaluation,
    SendOffer,
    handle_approve,
    handle_claim,
    handle_reevaluate,
    handle_reject,
    handle_send_offer,
)
from app.commands.notifications import MarkNotificationRead, handle_mark_read
from app.commands.offers import AcceptOffer, DeclineOffer, handle_accept_offer, handle_decline_offer
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
from app.projections.leads import (
    project_assessment_approved,
    project_assessment_rejected,
    project_lead_claimed,
    project_notification_read,
    project_offer_accepted,
    project_offer_declined,
    project_offer_sent,
    project_reevaluation_requested,
)
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
    dispatcher.register("LeadClaimed", project_lead_claimed)
    dispatcher.register("AssessmentApproved", project_assessment_approved)
    dispatcher.register("AssessmentRejected", project_assessment_rejected)
    dispatcher.register("ReevaluationRequested", project_reevaluation_requested)
    dispatcher.register("OfferSent", project_offer_sent)
    dispatcher.register("OfferAccepted", project_offer_accepted)
    dispatcher.register("OfferDeclined", project_offer_declined)
    dispatcher.register("NotificationRead", project_notification_read)
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
    bus.register(ClaimLead, handle_claim)
    bus.register(ApproveAssessment, handle_approve)
    bus.register(RejectAssessment, handle_reject)
    bus.register(RequestReevaluation, handle_reevaluate)
    bus.register(SendOffer, handle_send_offer)
    bus.register(AcceptOffer, handle_accept_offer)
    bus.register(DeclineOffer, handle_decline_offer)
    bus.register(MarkNotificationRead, handle_mark_read)
    return bus
