from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.domain.user.exceptions import InvalidMagicLinkTokenError
from api.domain.user.models import MagicLinkToken, User
from api.technical.auth.tokens import generate_opaque_token, hash_token
from api.technical.email.messages import render_magic_link_email
from api.technical.email.smtp import send_email
from config.auth import get_auth_config
from config.email import get_email_config


async def request_magic_link(session: AsyncSession, email: str) -> None:
    user = await session.scalar(select(User).where(User.email == email))
    if user is None:
        return

    raw_token = generate_opaque_token()
    config = get_auth_config()
    session.add(
        MagicLinkToken(
            user_id=user.id,
            token=hash_token(raw_token),
            expires_at=datetime.now(UTC) + timedelta(minutes=config.magic_link_ttl_minutes),
        )
    )
    await session.commit()

    frontend_url = get_email_config().frontend_url.rstrip("/")
    magic_link_url = f"{frontend_url}/login?magic_token={raw_token}"
    content = render_magic_link_email(
        language=user.preferred_language, magic_link_url=magic_link_url
    )
    await send_email(
        to=user.email,
        subject=content.subject,
        body=content.text_body,
        html_body=content.html_body,
    )


async def verify_magic_link_token(session: AsyncSession, raw_token: str) -> UUID:
    stored = await session.scalar(
        select(MagicLinkToken).where(MagicLinkToken.token == hash_token(raw_token))
    )
    if stored is None or stored.used_at is not None or stored.expires_at < datetime.now(UTC):
        raise InvalidMagicLinkTokenError

    stored.used_at = datetime.now(UTC)
    await session.commit()
    return stored.user_id
