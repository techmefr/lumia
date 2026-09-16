from collections.abc import AsyncIterator
from datetime import UTC, datetime

import pyotp
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from api.domain.user.exceptions import (
    InvalidTotpCodeError,
    TotpAlreadyEnabledError,
    TotpNotEnrolledError,
    TotpRequiredError,
)
from api.domain.user.models import Instance, RecoveryCode, User
from api.domain.user.totp_service import (
    SecondFactor,
    begin_enrolment,
    confirm_enrolment,
    count_unused_recovery_codes,
    disable_totp,
    is_totp_enabled,
    regenerate_recovery_codes,
    verify_second_factor,
)
from api.technical.auth.totp import RECOVERY_CODE_COUNT
from api.technical.crypto.secret_box import decrypt_secret
from config.database import get_engine


@pytest.fixture
async def session(db_schema: None) -> AsyncIterator[AsyncSession]:
    session_factory = async_sessionmaker(get_engine(), expire_on_commit=False)
    async with session_factory() as db_session:
        yield db_session


async def _create_user(session: AsyncSession) -> User:
    instance = Instance(max_accounts=10, disk_quota_mb=1000)
    session.add(instance)
    await session.flush()
    user = User(instance_id=instance.id, email="reader@example.com", username="reader")
    session.add(user)
    await session.commit()
    return user


def _code_for(secret: str) -> str:
    return pyotp.TOTP(secret).now()


async def _enable(session: AsyncSession, user: User) -> tuple[str, list[str]]:
    enrolment = await begin_enrolment(session, user)
    codes = await confirm_enrolment(session, user, _code_for(enrolment.secret))
    return enrolment.secret, codes


async def test_enrolment_stores_the_secret_encrypted(session: AsyncSession) -> None:
    user = await _create_user(session)

    enrolment = await begin_enrolment(session, user)

    assert user.totp_secret_encrypted is not None
    assert enrolment.secret not in user.totp_secret_encrypted
    assert decrypt_secret(user.totp_secret_encrypted) == enrolment.secret


async def test_starting_an_enrolment_does_not_turn_the_second_factor_on(
    session: AsyncSession,
) -> None:
    """A wrongly configured authenticator would otherwise lock the account out for good."""
    user = await _create_user(session)

    await begin_enrolment(session, user)

    assert not is_totp_enabled(user)


async def test_confirming_with_a_valid_code_turns_it_on(session: AsyncSession) -> None:
    user = await _create_user(session)
    enrolment = await begin_enrolment(session, user)

    await confirm_enrolment(session, user, _code_for(enrolment.secret))

    assert is_totp_enabled(user)


async def test_confirming_with_a_wrong_code_leaves_it_off(session: AsyncSession) -> None:
    user = await _create_user(session)
    await begin_enrolment(session, user)

    with pytest.raises(InvalidTotpCodeError):
        await confirm_enrolment(session, user, "000000")

    assert not is_totp_enabled(user)


async def test_confirming_without_an_enrolment_is_refused(session: AsyncSession) -> None:
    user = await _create_user(session)

    with pytest.raises(TotpNotEnrolledError):
        await confirm_enrolment(session, user, "000000")


async def test_starting_again_once_enabled_is_refused(session: AsyncSession) -> None:
    user = await _create_user(session)
    await _enable(session, user)

    with pytest.raises(TotpAlreadyEnabledError):
        await begin_enrolment(session, user)


async def test_confirming_twice_is_refused(session: AsyncSession) -> None:
    user = await _create_user(session)
    secret, _ = await _enable(session, user)

    with pytest.raises(TotpAlreadyEnabledError):
        await confirm_enrolment(session, user, _code_for(secret))


async def test_confirming_hands_out_a_full_set_of_recovery_codes(session: AsyncSession) -> None:
    user = await _create_user(session)

    _, codes = await _enable(session, user)

    assert len(codes) == RECOVERY_CODE_COUNT
    assert await count_unused_recovery_codes(session, user) == RECOVERY_CODE_COUNT


async def test_recovery_codes_are_stored_hashed(session: AsyncSession) -> None:
    user = await _create_user(session)

    _, codes = await _enable(session, user)

    stored = list(await session.scalars(select(RecoveryCode.code_hash)))
    assert not set(codes) & set(stored)
    assert not {code.replace("-", "") for code in codes} & set(stored)


async def test_an_account_without_a_second_factor_needs_nothing(session: AsyncSession) -> None:
    user = await _create_user(session)

    await verify_second_factor(session, user, None)


async def test_an_enabled_account_with_nothing_offered_is_told_a_code_is_expected(
    session: AsyncSession,
) -> None:
    user = await _create_user(session)
    await _enable(session, user)

    with pytest.raises(TotpRequiredError):
        await verify_second_factor(session, user, None)


async def test_an_empty_code_counts_as_nothing_offered(session: AsyncSession) -> None:
    user = await _create_user(session)
    await _enable(session, user)

    with pytest.raises(TotpRequiredError):
        await verify_second_factor(session, user, SecondFactor(code=""))


async def test_a_live_code_passes(session: AsyncSession) -> None:
    user = await _create_user(session)
    secret, _ = await _enable(session, user)
    # Confirming spent the current step; in real use the next sign-in falls in a later one.
    user.totp_last_used_step = None

    await verify_second_factor(session, user, SecondFactor(code=_code_for(secret)))


async def test_a_wrong_code_is_refused(session: AsyncSession) -> None:
    user = await _create_user(session)
    await _enable(session, user)

    with pytest.raises(InvalidTotpCodeError):
        await verify_second_factor(session, user, SecondFactor(code="000000"))


async def test_the_same_code_cannot_be_used_twice(session: AsyncSession) -> None:
    user = await _create_user(session)
    secret, _ = await _enable(session, user)
    user.totp_last_used_step = None
    code = _code_for(secret)

    await verify_second_factor(session, user, SecondFactor(code=code))

    with pytest.raises(InvalidTotpCodeError):
        await verify_second_factor(session, user, SecondFactor(code=code))


async def test_a_recovery_code_passes_and_is_spent(session: AsyncSession) -> None:
    user = await _create_user(session)
    _, codes = await _enable(session, user)

    await verify_second_factor(session, user, SecondFactor(recovery_code=codes[0]))

    assert await count_unused_recovery_codes(session, user) == RECOVERY_CODE_COUNT - 1


async def test_a_recovery_code_cannot_be_used_twice(session: AsyncSession) -> None:
    user = await _create_user(session)
    _, codes = await _enable(session, user)
    await verify_second_factor(session, user, SecondFactor(recovery_code=codes[0]))

    with pytest.raises(InvalidTotpCodeError):
        await verify_second_factor(session, user, SecondFactor(recovery_code=codes[0]))


async def test_a_recovery_code_typed_without_its_dashes_still_works(
    session: AsyncSession,
) -> None:
    user = await _create_user(session)
    _, codes = await _enable(session, user)

    await verify_second_factor(
        session, user, SecondFactor(recovery_code=codes[0].replace("-", "").upper())
    )


async def test_a_recovery_code_of_another_account_is_refused(session: AsyncSession) -> None:
    user = await _create_user(session)
    _, codes = await _enable(session, user)
    other = User(instance_id=user.instance_id, email="other@example.com", username="other")
    session.add(other)
    await session.commit()
    await _enable(session, other)

    with pytest.raises(InvalidTotpCodeError):
        await verify_second_factor(session, other, SecondFactor(recovery_code=codes[0]))


async def test_a_code_that_was_never_issued_is_refused(session: AsyncSession) -> None:
    user = await _create_user(session)
    await _enable(session, user)

    with pytest.raises(InvalidTotpCodeError):
        await verify_second_factor(session, user, SecondFactor(recovery_code="dead-beef-dead-beef"))


async def test_regenerating_retires_the_previous_set(session: AsyncSession) -> None:
    user = await _create_user(session)
    _, codes = await _enable(session, user)

    fresh = await regenerate_recovery_codes(session, user)

    assert not set(fresh) & set(codes)
    assert await count_unused_recovery_codes(session, user) == RECOVERY_CODE_COUNT
    with pytest.raises(InvalidTotpCodeError):
        await verify_second_factor(session, user, SecondFactor(recovery_code=codes[0]))


async def test_regenerating_without_a_second_factor_is_refused(session: AsyncSession) -> None:
    user = await _create_user(session)

    with pytest.raises(TotpNotEnrolledError):
        await regenerate_recovery_codes(session, user)


async def test_disabling_clears_the_secret_and_every_recovery_code(
    session: AsyncSession,
) -> None:
    user = await _create_user(session)
    await _enable(session, user)

    await disable_totp(session, user)

    assert not is_totp_enabled(user)
    assert user.totp_secret_encrypted is None
    assert user.totp_last_used_step is None
    assert await count_unused_recovery_codes(session, user) == 0


async def test_a_disabled_account_asks_for_nothing_again(session: AsyncSession) -> None:
    user = await _create_user(session)
    await _enable(session, user)
    await disable_totp(session, user)

    await verify_second_factor(session, user, None)


async def test_a_spent_recovery_code_is_kept_rather_than_deleted(session: AsyncSession) -> None:
    """A used code has to stay unusable; deleting it would make it indistinguishable from unknown."""
    user = await _create_user(session)
    _, codes = await _enable(session, user)

    await verify_second_factor(session, user, SecondFactor(recovery_code=codes[0]))

    stored = list(
        await session.scalars(select(RecoveryCode).where(RecoveryCode.user_id == user.id))
    )
    assert len(stored) == RECOVERY_CODE_COUNT
    spent = [entry for entry in stored if entry.used_at is not None]
    assert len(spent) == 1
    assert spent[0].used_at is not None and spent[0].used_at <= datetime.now(UTC)
