from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from api.domain.user.exceptions import InvalidCurrentPasswordError, InvalidMagicLinkTokenError
from api.domain.user.magic_link_service import verify_magic_link_token
from api.domain.user.models import User
from api.domain.user.refresh_token_service import revoke_all_refresh_tokens
from api.domain.user.totp_service import SecondFactor
from api.technical.auth.hashing import hash_password, verify_password


async def change_password(
    session: AsyncSession, user: User, *, current_password: str | None, new_password: str
) -> None:
    """Sets a new password for a signed-in reader, asking for the one in place first.

    An account created through SSO or only ever entered through a magic link has no password yet;
    there is then nothing to prove and the first one is set as is. Every session ends either way:
    a password is changed because the old one may be in someone else's hands, and the refresh
    tokens issued under it would outlive the change by a month.
    """
    if user.password_hash is not None and not (
        current_password and verify_password(current_password, user.password_hash)
    ):
        raise InvalidCurrentPasswordError

    user.password_hash = hash_password(new_password)
    await session.commit()
    await revoke_all_refresh_tokens(session, user.id)


async def reset_password(
    session: AsyncSession,
    raw_token: str,
    new_password: str,
    *,
    second_factor: SecondFactor | None = None,
) -> UUID:
    """Sets a new password from a magic-link token, for a reader who cannot supply the old one.

    The magic link is short-lived, single-use and reaches only the address on the account. It is
    not the whole proof once a second factor is on, though: a reset hands back a signed-in session,
    so a mailbox on its own must not be enough to walk past the authenticator.
    """
    user_id = await verify_magic_link_token(session, raw_token, second_factor=second_factor)
    user = await session.get(User, user_id)
    if user is None:  # pragma: no cover - a token cannot outlive the account it belongs to
        raise InvalidMagicLinkTokenError

    user.password_hash = hash_password(new_password)
    await session.commit()
    await revoke_all_refresh_tokens(session, user.id)
    return user.id
