"""תשובות שגיאה אחידות. ראו docs/08 §8.1."""

from flask import jsonify
from pydantic import ValidationError


def error_response(status: int, code: str, message: str, fields: dict | None = None):
    return jsonify({
        "error": {"code": code, "message": message, "fields": fields or {}}
    }), status


def validation_response(exc: ValidationError):
    aliases = {
        "full_name": "fullName",
        "institution_id": "institutionId",
        "license_no": "licenseNo",
        "refresh_token": "refreshToken",
    }
    fields: dict[str, str] = {}
    for err in exc.errors():
        loc = err.get("loc") or ()
        key = aliases.get(str(loc[-1]), str(loc[-1])) if loc else "body"
        message = str(err.get("msg", "ערך לא תקין")).removeprefix("Value error, ")
        fields[key] = message
    return error_response(400, "VALIDATION_ERROR", "הקלט אינו תקין", fields)
