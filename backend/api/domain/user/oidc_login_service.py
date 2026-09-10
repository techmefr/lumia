from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.domain.user.exceptions import InvalidSsoLoginAttemptError
from api.domain.user.models import OidcLoginAttempt
from api.technical.auth.tokens import generate_opaque_token, hash_token
from config.auth import get_auth_config


async def start_login_attempt(session: AsyncSession) -> tuple[str, str]:
    """Records a login in flight and returns the state and nonce to hand to the provider."""
    state = generate_opaque_token()
    nonce = generate_opaque_token()
    config = get_auth_config()
    session.add(
        OidcLoginAttempt(
            state=hash_token(state),
            nonce=nonce,
            expires_at=datetime.now(UTC) + timedelta(minutes=config.oidc_login_ttl_minutes),
        )
    )
    await session.commit()
    return state, nonce


async def consume_login_attempt(session: AsyncSession, state: str) -> str:
    """Spends the attempt the callback claims to answer and returns its nonce.

    Without this the `state` was decoration: anyone could have a victim's browser deliver an
    authorization code of their own choosing and log that browser into an account they control.
    Single use, because a state that is accepted twice is a state that can be replayed.
    """
    attempt = await session.scalar(
        select(OidcLoginAttempt).where(OidcLoginAttempt.state == hash_token(state))
    )
    if attempt is None or attempt.used_at is not None or attempt.expires_at < datetime.now(UTC):
        raise InvalidSsoLoginAttemptError
    attempt.used_at = datetime.now(UTC)
    await session.commit()
    return attempt.nonce
