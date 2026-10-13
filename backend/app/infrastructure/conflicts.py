"""זיהוי הפרת האינדקס הייחודי של rm_users.email (SQLite ו-SQL Server)."""

from sqlalchemy.exc import IntegrityError


def is_email_unique_violation(exc: IntegrityError) -> bool:
    parts = [str(exc).lower()]
    orig = getattr(exc, "orig", None)
    if orig is not None:
        parts.append(str(orig).lower())
    text = " ".join(parts)
    if "uq_rm_users_email" in text:
        return True
    return "unique" in text and "rm_users" in text and "email" in text
