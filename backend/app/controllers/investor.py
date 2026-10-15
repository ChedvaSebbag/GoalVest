"""Endpoints של פרופיל ויעדים. ראו docs/08 §8.3."""

from uuid import UUID

from flask import Blueprint, current_app, jsonify, request
from goalvest_core import BusinessRuleViolation, NotFound

from app.auth.require_role import require_role
from app.bootstrap import build_command_bus
from app.commands.goals import ArchiveGoal, CreateGoal, GoalData, UpdateGoal
from app.commands.investor_profile import AssessRiskProfile, CreateInvestorProfile
from app.commands.offers import AcceptOffer, DeclineOffer
from app.controllers.errors import error_response, rule_response
from app.controllers.http import actor_id, command_id, correlation_id, missing_command_id, parse_body
from app.infrastructure.db import get_db
from app.investor.schemas import GoalBody, GoalUpdateBody, ProfileBody, ReasonBody, RiskBody
from app.queries.goals import get_goal, investor_dashboard, list_goals
from app.queries.investor_profiles import get_profile
from app.queries.offers import get_offer, list_offers

investor_bp = Blueprint("investor", __name__)


def _goal_data(body: GoalBody) -> GoalData:
    return GoalData(
        goal_type=body.goal_type,
        title=body.title,
        initial_amount=body.initial_amount,
        monthly_deposit=body.monthly_deposit,
        target_amount=body.target_amount,
        target_date=body.target_date,
        flexibility=body.flexibility,
        liquidity_need=body.liquidity_need,
        excluded_channels=tuple(body.excluded_channels),
        preferred_channels=tuple(body.preferred_channels),
        preferred_institutions=tuple(str(item) for item in body.preferred_institutions),
    )


def _dispatch(command):
    try:
        result = build_command_bus(get_db(), current_app.extensions["projections"]).dispatch(command)
    except NotFound as exc:
        return error_response(404, exc.code, str(exc))
    except BusinessRuleViolation as exc:
        return rule_response(exc)
    return jsonify({"id": str(result.id), "version": result.version}), 201


@investor_bp.put("/investor/profile")
@require_role("INVESTOR")
def put_profile():
    body, error = parse_body(ProfileBody)
    if error is not None:
        return error
    key = command_id()
    if key is None:
        return missing_command_id()
    return _dispatch(CreateInvestorProfile(
        command_id=key,
        actor_id=actor_id(),
        birth_year=body.birth_year,
        marital_status=body.marital_status,
        monthly_income_range=body.monthly_income_range,
        has_emergency_fund=body.has_emergency_fund,
        existing_products=tuple(body.existing_products),
        correlation_id=correlation_id(),
    ))


@investor_bp.post("/investor/risk-assessment")
@require_role("INVESTOR")
def post_risk():
    body, error = parse_body(RiskBody)
    if error is not None:
        return error
    key = command_id()
    if key is None:
        return missing_command_id()
    return _dispatch(AssessRiskProfile(
        command_id=key,
        actor_id=actor_id(),
        answers=body.answers.as_dict(),
        correlation_id=correlation_id(),
    ))


@investor_bp.get("/investor/profile")
@require_role("INVESTOR")
def read_profile():
    return jsonify(get_profile(get_db(), actor_id()))


@investor_bp.post("/investor/goals")
@require_role("INVESTOR")
def post_goal():
    body, error = parse_body(GoalBody)
    if error is not None:
        return error
    key = command_id()
    if key is None:
        return missing_command_id()
    return _dispatch(CreateGoal(
        command_id=key,
        actor_id=actor_id(),
        data=_goal_data(body),
        correlation_id=correlation_id(),
    ))


@investor_bp.put("/investor/goals/<uuid:goal_id>")
@require_role("INVESTOR")
def put_goal(goal_id: UUID):
    body, error = parse_body(GoalUpdateBody)
    if error is not None:
        return error
    key = command_id()
    if key is None:
        return missing_command_id()
    return _dispatch(UpdateGoal(
        command_id=key,
        actor_id=actor_id(),
        goal_id=goal_id,
        data=_goal_data(body),
        consent_share_contact=body.consent_share_contact,
        correlation_id=correlation_id(),
    ))


@investor_bp.delete("/investor/goals/<uuid:goal_id>")
@require_role("INVESTOR")
def delete_goal(goal_id: UUID):
    key = command_id()
    if key is None:
        return missing_command_id()
    reason = ""
    payload = request.get_json(silent=True)
    if isinstance(payload, dict) and isinstance(payload.get("reason"), str):
        reason = payload["reason"].strip()
    return _dispatch(ArchiveGoal(
        command_id=key,
        actor_id=actor_id(),
        goal_id=goal_id,
        reason=reason,
        correlation_id=correlation_id(),
    ))


@investor_bp.get("/investor/dashboard")
@require_role("INVESTOR")
def read_dashboard():
    return jsonify(investor_dashboard(get_db(), actor_id()))


@investor_bp.get("/investor/offers")
@require_role("INVESTOR")
def read_offers():
    return jsonify(list_offers(get_db(), actor_id()))


@investor_bp.get("/investor/offers/<uuid:offer_id>")
@require_role("INVESTOR")
def read_offer(offer_id: UUID):
    offer = get_offer(get_db(), offer_id, actor_id())
    if offer is None:
        return error_response(404, "NOT_FOUND", "הפריט לא נמצא")
    return jsonify(offer)


@investor_bp.post("/investor/offers/<uuid:offer_id>/accept")
@require_role("INVESTOR")
def accept_offer(offer_id: UUID):
    key = command_id()
    if key is None:
        return missing_command_id()
    return _dispatch(AcceptOffer(
        command_id=key,
        actor_id=actor_id(),
        offer_id=offer_id,
        correlation_id=correlation_id(),
    ))


@investor_bp.post("/investor/offers/<uuid:offer_id>/decline")
@require_role("INVESTOR")
def decline_offer(offer_id: UUID):
    key = command_id()
    if key is None:
        return missing_command_id()
    reason = ""
    if request.get_json(silent=True) is not None:
        body, error = parse_body(ReasonBody)
        if error is not None:
            return error
        reason = body.reason
    return _dispatch(DeclineOffer(
        command_id=key,
        actor_id=actor_id(),
        offer_id=offer_id,
        reason=reason,
        correlation_id=correlation_id(),
    ))


@investor_bp.get("/investor/goals")
@require_role("INVESTOR")
def read_goals():
    return jsonify(list_goals(get_db(), actor_id()))


@investor_bp.get("/investor/goals/<uuid:goal_id>")
@require_role("INVESTOR")
def read_goal(goal_id: UUID):
    goal = get_goal(get_db(), goal_id, actor_id())
    if goal is None:
        return error_response(404, "NOT_FOUND", "הפריט לא נמצא")
    return jsonify(goal)
