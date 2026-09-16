from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from api.domain.user.exceptions import (
    InvalidTotpCodeError,
    TotpAlreadyEnabledError,
    TotpNotEnrolledError,
    TotpRequiredError,
)
from api.domain.user.models import RecoveryCode, User
from api.technical.auth.tokens import hash_token
from api.technical.auth.totp import (
    TotpEnrolment,
    build_enrolment,
    generate_recovery_codes,
    generate_totp_secret,
    normalise_recovery_code,
    verify_totp_code,
)
from api.technical.crypto.secret_box import decrypt_secret, encrypt_secret

#: What an authenticator app shows above the account, so a reader with several instances can tell
#: them apart. Not configurable: the instance has no name of its own to offer.
ISSUER = "Lumia"


@dataclass(frozen=True)
class SecondFactor:
    """What a reader offers instead of their authenticator being trusted on faith.

    Two fields rather than one: a six-digit code and a recovery code are checked differently and
    have different consequences — one may be replayed within its window, the other is spent.
    """

    code: str | None = None
    recovery_code: str | None = None


def is_totp_enabled(user: User) -> bool:
    return user.totp_confirmed_at is not None


async def begin_enrolment(session: AsyncSession, user: User) -> TotpEnrolment:
    """Draws a fresh secret and hands back what the authenticator needs to store it.

    Starting again replaces whatever draft was there: a reader who scanned a code into the wrong
    app has no other way out. An enrolment already confirmed is refused instead, so a stolen access
    token cannot silently swap the second factor for one of its own.
    """
    if is_totp_enabled(user):
        raise TotpAlreadyEnabledError

    secret = generate_totp_secret()
    user.totp_secret_encrypted = encrypt_secret(secret)
    user.totp_last_used_step = None
    await session.commit()
    return build_enrolment(secret, account_name=user.email, issuer=ISSUER)


async def confirm_enrolment(session: AsyncSession, user: User, code: str) -> list[str]:
    """Turns the second factor on, once a code proves the authenticator is really set up.

    Returns the recovery codes, the only time they exist in readable form. They are minted here
    rather than at `begin_enrolment` so an abandoned draft never leaves usable codes behind.
    """
    if is_totp_enabled(user):
        raise TotpAlreadyEnabledError
    if user.totp_secret_encrypted is None:
        raise TotpNotEnrolledError

    step = verify_totp_code(decrypt_secret(user.totp_secret_encrypted), code)
    if step is None:
        raise InvalidTotpCodeError

    user.totp_confirmed_at = datetime.now(UTC)
    user.totp_last_used_step = step
    return await _replace_recovery_codes(session, user)


async def regenerate_recovery_codes(session: AsyncSession, user: User) -> list[str]:
    """Issues a new set, retiring the old one — what a reader who used or lost theirs needs."""
    if not is_totp_enabled(user):
        raise TotpNotEnrolledError
    return await _replace_recovery_codes(session, user)


async def disable_totp(session: AsyncSession, user: User) -> None:
    """Removes the second factor and everything that could still stand in for it."""
    user.totp_secret_encrypted = None
    user.totp_confirmed_at = None
    user.totp_last_used_step = None
    await session.execute(delete(RecoveryCode).where(RecoveryCode.user_id == user.id))
    await session.commit()


async def verify_second_factor(
    session: AsyncSession, user: User, second_factor: SecondFactor | None
) -> None:
    """Checks the second factor of an account that has one, and does nothing for one that has not.

    `TotpRequiredError` is raised apart from `InvalidTotpCodeError` on purpose: the caller has
    already proved the first factor, so telling it that a code is expected reveals nothing it could
    not learn by trying, and without that distinction the sign-in form cannot know to ask.
    """
    if not is_totp_enabled(user):
        return
    if second_factor is None or not (second_factor.code or second_factor.recovery_code):
        raise TotpRequiredError

    if second_factor.recovery_code:
        await _spend_recovery_code(session, user, second_factor.recovery_code)
        return

    code = second_factor.code
    secret = user.totp_secret_encrypted
    if code is None or secret is None:  # pragma: no cover - enabling always stores a secret
        raise InvalidTotpCodeError
    step = verify_totp_code(
        decrypt_secret(secret),
        code,
        last_used_step=user.totp_last_used_step,
    )
    if step is None:
        raise InvalidTotpCodeError

    user.totp_last_used_step = step
    await session.commit()


async def count_unused_recovery_codes(session: AsyncSession, user: User) -> int:
    codes = await session.scalars(
        select(RecoveryCode).where(RecoveryCode.user_id == user.id, RecoveryCode.used_at.is_(None))
    )
    return len(list(codes))


async def _replace_recovery_codes(session: AsyncSession, user: User) -> list[str]:
    await session.execute(delete(RecoveryCode).where(RecoveryCode.user_id == user.id))
    codes = generate_recovery_codes()
    for code in codes:
        session.add(
            RecoveryCode(user_id=user.id, code_hash=hash_token(normalise_recovery_code(code)))
        )
    await session.commit()
    return codes


async def _spend_recovery_code(session: AsyncSession, user: User, raw_code: str) -> None:
    """Consumes a recovery code, looked up by its hash so nothing readable is ever compared.

    Single use: a code that has been spent is kept in place and refused, rather than deleted, so a
    second attempt with the same one cannot be mistaken for a code that was never issued.
    """
    stored = await session.scalar(
        select(RecoveryCode).where(
            RecoveryCode.user_id == user.id,
            RecoveryCode.code_hash == hash_token(normalise_recovery_code(raw_code)),
        )
    )
    if stored is None or stored.used_at is not None:
        raise InvalidTotpCodeError

    stored.used_at = datetime.now(UTC)
    await session.commit()
