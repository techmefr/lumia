from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID

import jwt

from config.auth import get_auth_config


class InvalidAccessTokenError(Exception):
    pass


@dataclass(frozen=True)
class AccessClaims:
    user_id: UUID
    session_version: int


def create_access_token(user_id: UUID, session_version: int = 0) -> str:
    config = get_auth_config()
    now = datetime.now(UTC)
    payload = {
        "sub": str(user_id),
        "sv": session_version,
        "iat": now,
        "exp": now + timedelta(minutes=config.access_token_ttl_minutes),
    }
    return jwt.encode(payload, config.jwt_secret, algorithm=config.jwt_algorithm)


def decode_access_claims(token: str) -> AccessClaims:
    config = get_auth_config()
    try:
        payload = jwt.decode(token, config.jwt_secret, algorithms=[config.jwt_algorithm])
    except jwt.PyJWTError as exc:
        raise InvalidAccessTokenError from exc
    try:
        user_id = UUID(payload["sub"])
        session_version = int(payload.get("sv", 0))
    except (KeyError, ValueError, TypeError) as exc:
        raise InvalidAccessTokenError from exc
    return AccessClaims(user_id=user_id, session_version=session_version)


def decode_access_token(token: str) -> UUID:
    return decode_access_claims(token).user_id
