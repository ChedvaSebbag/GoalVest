"""Endpoints של אוטנטיקציה וגופים פיננסיים. ראו docs/08 §8.2."""

from uuid import UUID

from flask import Blueprint, current_app, jsonify, request
from flask_jwt_extended import get_jwt_identity
from goalvest_core import BusinessRuleViolation, EmailAlreadyExists
from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError

from app.auth.errors import Unauthorized, UnknownInstitution
from app.auth.limiter import limiter, login_rate_key
from app.auth.require_role import require_role
from app.auth.schemas import LoginBody, RefreshBody, RegisterBody
from app.auth.tokens import issue_tokens, revoke_refresh, rotate_refresh
from app.bootstrap import build_command_bus
from app.commands.register_user import RegisterUser
from app.controllers.errors import error_response, validation_response
from app.infrastructure.conflicts import is_email_unique_violation
from app.infrastructure.db import get_db
from app.queries.institutions import list_institutions
from app.queries.users import authenticate, get_user

auth_bp = Blueprint("auth", __name__)


@auth_bp.post("/auth/register")
def register():
    body, error = _body(RegisterBody)
    if error is not None:
        return error
    command_id = _idempotency_key()
    if command_id is None:
        return error_response(400, "VALIDATION_ERROR", "הקלט אינו תקין", {"Idempotency-Key": "חסר או אינו UUID"})
    command = RegisterUser(
        command_id=command_id,
        email=body.email,
        full_name=body.full_name,
        phone=body.phone,
        password=body.password,
        role=body.role,
        institution_id=body.institution_id,
        license_no=body.license_no,
        correlation_id=request.headers.get("X-Correlation-Id"),
    )
    try:
        result = build_command_bus(get_db(), current_app.extensions["projections"]).dispatch(command)
    except EmailAlreadyExists as exc:
        return error_response(409, exc.code, str(exc))
    except UnknownInstitution:
        return error_response(
            400,
            "VALIDATION_ERROR",
            "הקלט אינו תקין",
            {"institutionId": "יש לבחור גוף מהרשימה"},
        )
    except BusinessRuleViolation as exc:
        return error_response(422, exc.code, str(exc))
    except IntegrityError as exc:
        if is_email_unique_violation(exc):
            return error_response(409, "EMAIL_EXISTS", "כתובת האימייל כבר רשומה")
        raise
    return jsonify({"id": str(result.id), "version": result.version}), 201


@auth_bp.post("/auth/login")
@limiter.limit("5 per 15 minutes", key_func=login_rate_key)
def login():
    body, error = _body(LoginBody)
    if error is not None:
        return error
    user = authenticate(get_db(), body.email, body.password)
    if user is None:
        return error_response(401, "UNAUTHORIZED", "אימייל או סיסמה שגויים")
    tokens = issue_tokens(user["id"], user["role"], user["institutionId"])
    return jsonify({**tokens, "user": _session_user(user)})


@auth_bp.post("/auth/refresh")
def refresh():
    body, error = _body(RefreshBody)
    if error is not None:
        return error
    try:
        tokens, user_id = rotate_refresh(get_db(), body.refresh_token)
    except Unauthorized as exc:
        return error_response(401, "UNAUTHORIZED", str(exc))
    user = get_user(get_db(), UUID(user_id))
    if user is None:
        return error_response(401, "UNAUTHORIZED", "תוקף ההתחברות פג")
    return jsonify({**tokens, "user": _session_user(user)})


@auth_bp.post("/auth/logout")
@require_role("INVESTOR", "AGENT")
def logout():
    body, error = _body(RefreshBody)
    if error is not None:
        return error
    try:
        revoke_refresh(get_db(), body.refresh_token, str(get_jwt_identity()))
    except Unauthorized as exc:
        return error_response(401, "UNAUTHORIZED", str(exc))
    return "", 204


@auth_bp.get("/auth/me")
@require_role("INVESTOR", "AGENT")
def me():
    user = get_user(get_db(), UUID(str(get_jwt_identity())))
    if user is None:
        return error_response(401, "UNAUTHORIZED", "נדרשת התחברות")
    return jsonify(user)


@auth_bp.get("/institutions")
def institutions():
    return jsonify({"items": list_institutions()})


def _body(model):
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return None, error_response(400, "VALIDATION_ERROR", "הקלט אינו תקין")
    try:
        return model.model_validate(payload), None
    except ValidationError as exc:
        return None, validation_response(exc)


def _idempotency_key() -> UUID | None:
    raw = (request.headers.get("Idempotency-Key") or "").strip()
    if not raw:
        return None
    try:
        return UUID(raw)
    except ValueError:
        return None


def _session_user(user: dict) -> dict:
    return {"id": user["id"], "role": user["role"], "fullName": user["fullName"]}
