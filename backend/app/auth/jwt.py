"""אתחול flask-jwt-extended ואזהרה אם JWT_SECRET אינו סוד אמיתי."""

import sys
from datetime import timedelta

from flask import Flask, jsonify, make_response
from flask_jwt_extended import JWTManager

from app.auth.tokens import is_revoked
from app.infrastructure.db import get_db

jwt = JWTManager()
_callbacks_ready = False


def init_jwt(app: Flask) -> None:
    secret = app.config.get("JWT_SECRET") or ""
    if not secret or secret == "change-me":
        print(
            "אזהרה: JWT_SECRET חסר או שווה ל-change-me. הגדירו סוד אמיתי בקובץ .env.",
            file=sys.stderr,
        )
    app.config["JWT_SECRET_KEY"] = secret or "change-me"
    app.config["JWT_ACCESS_TOKEN_EXPIRES"] = timedelta(minutes=int(app.config["JWT_ACCESS_MINUTES"]))
    app.config["JWT_REFRESH_TOKEN_EXPIRES"] = timedelta(days=int(app.config["JWT_REFRESH_DAYS"]))
    jwt.init_app(app)
    _register_callbacks()


def _register_callbacks() -> None:
    global _callbacks_ready
    if _callbacks_ready:
        return

    @jwt.token_in_blocklist_loader
    def _blocked(_header, payload: dict) -> bool:
        jti = payload.get("jti")
        if not isinstance(jti, str):
            return True
        return is_revoked(get_db(), jti)

    @jwt.unauthorized_loader
    def _missing(_reason: str):
        return _unauthorized("נדרשת התחברות")

    @jwt.invalid_token_loader
    def _invalid(_reason: str):
        return _unauthorized("נדרשת התחברות")

    @jwt.expired_token_loader
    def _expired(_header, _payload):
        return _unauthorized("תוקף ההתחברות פג")

    _callbacks_ready = True


def _unauthorized(message: str):
    body = jsonify({"error": {"code": "UNAUTHORIZED", "message": message, "fields": {}}})
    return make_response(body, 401)
