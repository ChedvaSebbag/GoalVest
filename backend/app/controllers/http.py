"""קריאת גוף פקודה ומזהה המשתמש. בלי חוקים עסקיים."""

from uuid import UUID

from flask import request
from flask_jwt_extended import get_jwt_identity
from pydantic import ValidationError

from app.controllers.errors import error_response, validation_response


def parse_body(model):
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return None, error_response(400, "VALIDATION_ERROR", "הקלט אינו תקין")
    try:
        return model.model_validate(payload), None
    except ValidationError as exc:
        return None, validation_response(exc)


def command_id() -> UUID | None:
    raw = (request.headers.get("Idempotency-Key") or "").strip()
    if not raw:
        return None
    try:
        return UUID(raw)
    except ValueError:
        return None


def missing_command_id():
    return error_response(400, "VALIDATION_ERROR", "הקלט אינו תקין", {"Idempotency-Key": "חסר או אינו UUID"})


def actor_id() -> UUID:
    return UUID(str(get_jwt_identity()))


def correlation_id() -> str | None:
    return request.headers.get("X-Correlation-Id")
