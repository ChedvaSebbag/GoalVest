"""הגבלת ניסיונות התחברות: 5 בחלון של 15 דקות לאימייל. ראו docs/12 §12.1."""

from flask import request
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from goalvest_core.accounts import normalize_email

limiter = Limiter(key_func=get_remote_address, storage_uri="memory://")


def login_rate_key() -> str:
    payload = request.get_json(silent=True)
    if isinstance(payload, dict):
        raw = payload.get("email")
        if isinstance(raw, str) and raw.strip():
            return normalize_email(raw)
    return get_remote_address()
