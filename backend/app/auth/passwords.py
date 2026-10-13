"""bcrypt בעלות 12. ראו docs/12 §12.1."""

import bcrypt

_BCRYPT_ROUNDS = 12
_dummy_hash: str | None = None


def hash_password(password: str) -> str:
    hashed = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt(rounds=_BCRYPT_ROUNDS))
    return hashed.decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except ValueError:
        return False


def verify_or_dummy(password: str, password_hash: str | None) -> bool:
    """בודק מול hash אמיתי, או מול hash קבוע אם המשתמש לא קיים, כדי לא לחשוף זאת בזמן התגובה."""
    global _dummy_hash
    if password_hash is None:
        if _dummy_hash is None:
            _dummy_hash = hash_password("not-a-real-password")
        verify_password(password, _dummy_hash)
        return False
    return verify_password(password, password_hash)
