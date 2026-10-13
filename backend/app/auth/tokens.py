"""הנפקת JWT ופסילת Refresh. ראו docs/12 §12.1."""

from datetime import UTC, datetime
from uuid import UUID

import sqlalchemy as sa
from flask_jwt_extended import create_access_token, create_refresh_token, decode_token
from flask_jwt_extended.exceptions import JWTDecodeError
from jwt.exceptions import PyJWTError
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth.errors import Unauthorized
from app.infrastructure.serialization import to_naive_utc
from app.infrastructure.tables import revoked_tokens


def issue_tokens(user_id: str, role: str, institution_id: str | None) -> dict[str, str]:
    claims = {"role": role, "institution_id": institution_id}
    return {
        "accessToken": create_access_token(identity=user_id, additional_claims=claims),
        "refreshToken": create_refresh_token(identity=user_id, additional_claims=claims),
    }


def is_revoked(session: Session, jti: str) -> bool:
    try:
        key = UUID(jti)
    except ValueError:
        return True
    row = session.execute(sa.select(revoked_tokens.c.jti).where(revoked_tokens.c.jti == key)).first()
    return row is not None


def rotate_refresh(session: Session, refresh_token: str) -> tuple[dict[str, str], str]:
    payload = _decode_refresh(refresh_token)
    if is_revoked(session, payload["jti"]):
        raise Unauthorized("תוקף ההתחברות פג")
    _store_revocation(session, payload)
    session.commit()
    user_id = payload["sub"]
    role = payload.get("role")
    institution_id = payload.get("institution_id")
    if not isinstance(user_id, str) or not isinstance(role, str):
        raise Unauthorized("תוקף ההתחברות פג")
    if institution_id is not None and not isinstance(institution_id, str):
        raise Unauthorized("תוקף ההתחברות פג")
    return issue_tokens(user_id, role, institution_id), user_id


def revoke_refresh(session: Session, refresh_token: str, expected_user_id: str) -> None:
    payload = _decode_refresh(refresh_token)
    if payload.get("sub") != expected_user_id:
        raise Unauthorized("תוקף ההתחברות פג")
    if is_revoked(session, payload["jti"]):
        return
    _store_revocation(session, payload)
    try:
        session.commit()
    except IntegrityError:
        session.rollback()


def _decode_refresh(refresh_token: str) -> dict:
    try:
        payload = decode_token(refresh_token)
    except (JWTDecodeError, PyJWTError) as exc:
        raise Unauthorized("תוקף ההתחברות פג") from exc
    if payload.get("type") != "refresh":
        raise Unauthorized("תוקף ההתחברות פג")
    return payload


def _store_revocation(session: Session, payload: dict) -> None:
    expires = datetime.fromtimestamp(int(payload["exp"]), tz=UTC)
    session.execute(
        sa.insert(revoked_tokens).values(
            jti=UUID(payload["jti"]),
            expires_at=to_naive_utc(expires),
            revoked_at=to_naive_utc(datetime.now(UTC)),
        )
    )
