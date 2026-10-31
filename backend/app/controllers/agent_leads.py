"""דשבורד ולידים של סוכן. ראו docs/08 §8.5."""

from datetime import datetime
from uuid import UUID

from flask import Blueprint, current_app, jsonify, request
from goalvest_core import BusinessRuleViolation, ConcurrencyError, Forbidden, NotFound

from app.auth.require_role import require_role
from app.bootstrap import build_command_bus
from app.commands.leads import (
    ApproveAssessment,
    ClaimLead,
    RejectAssessment,
    RequestReevaluation,
    SendOffer,
)
from app.controllers.errors import error_response, rule_response
from app.controllers.http import actor_id, command_id, correlation_id, missing_command_id, parse_body
from app.infrastructure.db import get_db
from app.investor.schemas import NoteBody, OfferBody, ReasonBody
from app.queries.leads import agent_institution, dashboard, lead_details, list_leads, product_interest

agent_leads_bp = Blueprint("agent_leads", __name__)


def _dispatch(command):
    try:
        result = build_command_bus(get_db(), current_app.extensions["projections"]).dispatch(command)
    except NotFound as exc:
        return error_response(404, exc.code, str(exc))
    except Forbidden as exc:
        return error_response(403, exc.code, str(exc))
    except BusinessRuleViolation as exc:
        return rule_response(exc)
    except ConcurrencyError:
        return error_response(409, "CONFLICT", "הליד עודכן בינתיים. רעננו ונסו שוב")
    return jsonify({"id": str(result.id), "version": result.version}), 201


def _institution():
    institution_id = agent_institution(get_db(), actor_id())
    if institution_id is None:
        return None, error_response(403, "FORBIDDEN", "אין הרשאה לפעולה הזו")
    return institution_id, None


@agent_leads_bp.get("/agent/dashboard")
@require_role("AGENT")
def read_dashboard():
    institution_id, error = _institution()
    if error is not None:
        return error
    return jsonify(dashboard(get_db(), institution_id))


@agent_leads_bp.get("/agent/dashboard/product-interest")
@require_role("AGENT")
def read_interest():
    institution_id, error = _institution()
    if error is not None:
        return error
    return jsonify(product_interest(get_db(), institution_id))


@agent_leads_bp.get("/agent/leads")
@require_role("AGENT")
def read_leads():
    institution_id, error = _institution()
    if error is not None:
        return error
    status = (request.args.get("status") or "").strip() or None
    goal_type = (request.args.get("goalType") or "").strip() or None
    min_score, score_error = _optional_int("minScore")
    if score_error is not None:
        return score_error
    page, page_error = _page()
    if page_error is not None:
        return page_error
    since, since_error = _since()
    if since_error is not None:
        return since_error
    return jsonify(list_leads(
        get_db(),
        institution_id,
        status=status,
        min_score=min_score,
        goal_type=goal_type,
        page=page,
        sort=request.args.get("sort"),
        since=since,
    ))


@agent_leads_bp.get("/agent/leads/<uuid:request_id>")
@require_role("AGENT")
def read_lead(request_id: UUID):
    institution_id, error = _institution()
    if error is not None:
        return error
    details = lead_details(get_db(), request_id, institution_id, actor_id())
    if details is None:
        return error_response(404, "NOT_FOUND", "הפריט לא נמצא")
    return jsonify(details)


@agent_leads_bp.post("/agent/leads/<uuid:request_id>/claim")
@require_role("AGENT")
def claim_lead(request_id: UUID):
    key = command_id()
    if key is None:
        return missing_command_id()
    return _dispatch(ClaimLead(
        command_id=key,
        actor_id=actor_id(),
        request_id=request_id,
        correlation_id=correlation_id(),
    ))


@agent_leads_bp.post("/agent/leads/<uuid:request_id>/assessment/approve")
@require_role("AGENT")
def approve_lead(request_id: UUID):
    key = command_id()
    if key is None:
        return missing_command_id()
    note = ""
    if request.get_json(silent=True) is not None:
        body, error = parse_body(NoteBody)
        if error is not None:
            return error
        note = body.note
    return _dispatch(ApproveAssessment(
        command_id=key,
        actor_id=actor_id(),
        request_id=request_id,
        note=note,
        correlation_id=correlation_id(),
    ))


@agent_leads_bp.post("/agent/leads/<uuid:request_id>/assessment/reject")
@require_role("AGENT")
def reject_lead(request_id: UUID):
    key = command_id()
    if key is None:
        return missing_command_id()
    body, error = parse_body(NoteBody)
    if error is not None:
        return error
    return _dispatch(RejectAssessment(
        command_id=key,
        actor_id=actor_id(),
        request_id=request_id,
        note=body.note,
        correlation_id=correlation_id(),
    ))


@agent_leads_bp.post("/agent/leads/<uuid:request_id>/reevaluate")
@require_role("AGENT")
def reevaluate_lead(request_id: UUID):
    key = command_id()
    if key is None:
        return missing_command_id()
    body, error = parse_body(ReasonBody)
    if error is not None:
        return error
    return _dispatch(RequestReevaluation(
        command_id=key,
        actor_id=actor_id(),
        request_id=request_id,
        reason=body.reason,
        correlation_id=correlation_id(),
    ))


@agent_leads_bp.post("/agent/leads/<uuid:request_id>/offers")
@require_role("AGENT")
def send_offer(request_id: UUID):
    key = command_id()
    if key is None:
        return missing_command_id()
    body, error = parse_body(OfferBody)
    if error is not None:
        return error
    return _dispatch(SendOffer(
        command_id=key,
        actor_id=actor_id(),
        request_id=request_id,
        items=tuple({"product_id": item.product_id, "percent": item.percent} for item in body.items),
        message=body.message,
        correlation_id=correlation_id(),
    ))


def _optional_int(name: str):
    raw = (request.args.get(name) or "").strip()
    if not raw:
        return None, None
    try:
        return int(raw), None
    except ValueError:
        return None, error_response(400, "VALIDATION_ERROR", "הקלט אינו תקין", {name: "מספר שלם"})


def _page():
    raw = (request.args.get("page") or "1").strip()
    try:
        page = int(raw)
    except ValueError:
        return None, error_response(400, "VALIDATION_ERROR", "הקלט אינו תקין", {"page": "מספר שלם"})
    if page < 1:
        return None, error_response(400, "VALIDATION_ERROR", "הקלט אינו תקין", {"page": "מ-1"})
    return page, None


def _since():
    raw = (request.args.get("since") or "").strip()
    if not raw:
        return None, None
    try:
        return datetime.fromisoformat(raw), None
    except ValueError:
        return None, error_response(400, "VALIDATION_ERROR", "הקלט אינו תקין", {"since": "תאריך לא תקין"})
