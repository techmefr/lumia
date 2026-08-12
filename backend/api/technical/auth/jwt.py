from datetime import UTC, datetime, timedelta
from uuid import UUID

import jwt

from config.auth import get_auth_config


class InvalidAccessTokenError(Exception):
    pass


def create_access_token(user_id: UUID) -> str:
    config = get_auth_config()
    now = datetime.now(UTC)
    payload = {
        "sub": str(user_id),
        "iat": now,
        "exp": now + timedelta(minutes=config.access_token_ttl_minutes),
    }
    return jwt.encode(payload, config.jwt_secret, algorithm=config.jwt_algorithm)


def decode_access_token(token: str) -> UUID:
    config = get_auth_config()
    try:
        payload = jwt.decode(token, config.jwt_secret, algorithms=[config.jwt_algorithm])
    except jwt.PyJWTError as exc:
        raise InvalidAccessTokenError from exc
    try:
        return UUID(payload["sub"])
    except (KeyError, ValueError) as exc:
        raise InvalidAccessTokenError from exc
