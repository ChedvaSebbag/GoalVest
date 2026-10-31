"""Endpoints של בקשת השקעה. ראו docs/08 §8.3."""

# Controller layer (MVC) as a Flask Blueprint, registered under /api.
# Responsibilities only: role check (@require_role), body validation (Pydantic via parse_body),
# reading the Idempotency-Key, building the Command and mapping domain errors to HTTP
# (NotFound -> 404, BusinessRuleViolation -> 422). No business logic. Writes return 201 {id, version};
# reads go through the query services.

from uuid import UUID

from flask import Blueprint, current_app, jsonify, request
from goalvest_core import BusinessRuleViolation, NotFound

from app.auth.require_role import require_role
from app.bootstrap import build_command_bus
from app.commands.requests import CancelInvestmentRequest, SubmitInvestmentRequest
from app.controllers.errors import error_response, rule_response
from app.controllers.http import actor_id, command_id, correlation_id, missing_command_id, parse_body
from app.infrastructure.db import get_db
from app.investor.schemas import CancelBody, SubmitBody
from app.queries.requests import timeline_for

requests_bp = Blueprint("requests", __name__)


def _dispatch(command):
    try:
        result = build_command_bus(get_db(), current_app.extensions["projections"]).dispatch(command)
    except NotFound as exc:
        return error_response(404, exc.code, str(exc))
    except BusinessRuleViolation as exc:
        return rule_response(exc)
    return jsonify({"id": str(result.id), "version": result.version}), 201


@requests_bp.post("/requests")
@require_role("INVESTOR")
def submit_request():
    body, error = parse_body(SubmitBody)
    if error is not None:
        return error
    key = command_id()
    if key is None:
        return missing_command_id()
    return _dispatch(SubmitInvestmentRequest(
        command_id=key,
        actor_id=actor_id(),
        goal_id=body.goal_id,
        consent_share_contact=body.consent_share_contact,
        correlation_id=correlation_id(),
    ))


@requests_bp.post("/requests/<uuid:request_id>/cancel")
@require_role("INVESTOR")
def cancel_request(request_id: UUID):
    key = command_id()
    if key is None:
        return missing_command_id()
    reason = ""
    payload = request.get_json(silent=True)
    if isinstance(payload, dict):
        body, error = parse_body(CancelBody)
        if error is not None:
            return error
        reason = body.reason
    return _dispatch(CancelInvestmentRequest(
        command_id=key,
        actor_id=actor_id(),
        request_id=request_id,
        reason=reason,
        correlation_id=correlation_id(),
    ))


@requests_bp.get("/requests/<uuid:request_id>/timeline")
@require_role("INVESTOR")
def read_timeline(request_id: UUID):
    items = timeline_for(get_db(), request_id, actor_id())
    if items is None:
        return error_response(404, "NOT_FOUND", "הפריט לא נמצא")
    return jsonify(items)
