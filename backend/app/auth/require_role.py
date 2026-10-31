"""בדיקת תפקיד על Endpoint. הרשאות אמיתיות נשארות בשרת. ראו docs/12 §12.2."""

# Endpoint authorization: @require_role("INVESTOR" | "AGENT"). Missing/invalid JWT -> 401,
# wrong role -> 403. Resource ownership is enforced in handlers/queries, which answer 404 for
# another user's or another institution's data. Client-side guards are navigation only.

from collections.abc import Callable
from functools import wraps

from flask import jsonify
from flask_jwt_extended import get_jwt, verify_jwt_in_request


def require_role(*roles: str) -> Callable:
    def decorator(fn: Callable) -> Callable:
        @wraps(fn)
        def wrapper(*args, **kwargs):
            verify_jwt_in_request()
            role = get_jwt().get("role")
            if role not in roles:
                return jsonify({
                    "error": {
                        "code": "FORBIDDEN",
                        "message": "אין הרשאה לפעולה הזו",
                        "fields": {},
                    }
                }), 403
            return fn(*args, **kwargs)

        return wrapper

    return decorator


__all__ = ["require_role"]
