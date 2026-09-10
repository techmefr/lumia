from collections.abc import AsyncIterator

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from api.domain.user.exceptions import SsoNotConfiguredError, SsoSubjectMismatchError
from api.domain.user.models import Instance, Role, User
from api.domain.user.sso_service import ensure_sso_configured, get_or_create_sso_user
from api.technical.auth.hashing import hash_password
from config.database import get_engine


@pytest.fixture
async def session(db_schema: None) -> AsyncIterator[AsyncSession]:
    session_factory = async_sessionmaker(get_engine(), expire_on_commit=False)
    async with session_factory() as db_session:
        yield db_session


async def _create_instance(session: AsyncSession, *, oidc_issuer: str | None) -> Instance:
    instance = Instance(max_accounts=10, disk_quota_mb=1000, oidc_issuer=oidc_issuer)
    session.add(instance)
    await session.commit()
    return instance


def test_ensure_sso_configured_rejects_an_instance_without_oidc_issuer() -> None:
    instance = Instance(max_accounts=10, disk_quota_mb=1000)
    with pytest.raises(SsoNotConfiguredError):
        ensure_sso_configured(instance)


def test_ensure_sso_configured_accepts_an_instance_with_oidc_issuer() -> None:
    instance = Instance(max_accounts=10, disk_quota_mb=1000, oidc_issuer="https://idp.example.com")
    ensure_sso_configured(instance)


async def test_get_or_create_sso_user_provisions_a_new_member_on_first_login(
    session: AsyncSession,
) -> None:
    instance = await _create_instance(session, oidc_issuer="https://idp.example.com")
    user = await get_or_create_sso_user(
        session, instance, sub="sso-subject-1", email="new@example.com"
    )
    assert user.sso_subject == "sso-subject-1"
    assert user.password_hash is None
    assert user.role.value == "member"


async def test_get_or_create_sso_user_reuses_the_existing_user_for_a_known_sub(
    session: AsyncSession,
) -> None:
    instance = await _create_instance(session, oidc_issuer="https://idp.example.com")
    first = await get_or_create_sso_user(
        session, instance, sub="sso-subject-2", email="known@example.com"
    )
    second = await get_or_create_sso_user(
        session, instance, sub="sso-subject-2", email="known@example.com"
    )
    assert first.id == second.id


async def test_a_known_email_is_linked_to_the_existing_account(session: AsyncSession) -> None:
    """The reader signed up locally, then their administrator turned SSO on. The provider hands
    us a subject we have never seen for an address we already know: that is the same person, and
    the email column is unique anyway, so provisioning a second row could only fail."""
    instance = await _create_instance(session, oidc_issuer="https://idp.example.com")
    local = User(
        instance_id=instance.id,
        email="known@example.com",
        username="known",
        password_hash=hash_password("correct-horse-battery-staple"),
    )
    session.add(local)
    await session.commit()

    user = await get_or_create_sso_user(
        session, instance, sub="sso-subject-3", email="known@example.com"
    )

    assert user.id == local.id
    assert user.sso_subject == "sso-subject-3"
    # Their password still works: linking a provider is not a reason to lock a way in.
    assert user.password_hash is not None
    assert await session.scalar(select(func.count()).select_from(User)) == 1


async def test_a_linked_account_keeps_its_role(session: AsyncSession) -> None:
    """Signing in through the provider must not demote the administrator to a member."""
    instance = await _create_instance(session, oidc_issuer="https://idp.example.com")
    admin = User(
        instance_id=instance.id,
        email="admin@example.com",
        username="admin",
        role=Role.ADMIN,
    )
    session.add(admin)
    await session.commit()

    user = await get_or_create_sso_user(
        session, instance, sub="sso-subject-4", email="admin@example.com"
    )

    assert user.role == Role.ADMIN


async def test_an_account_already_linked_to_another_subject_is_refused(
    session: AsyncSession,
) -> None:
    """Two subjects claiming one address means either a provider that recycles addresses or a
    take-over attempt. Neither is worth guessing at, and silently moving the account to the new
    subject would hand it to whoever asked last."""
    instance = await _create_instance(session, oidc_issuer="https://idp.example.com")
    await get_or_create_sso_user(session, instance, sub="first-subject", email="one@example.com")

    with pytest.raises(SsoSubjectMismatchError):
        await get_or_create_sso_user(
            session, instance, sub="second-subject", email="one@example.com"
        )

    assert await session.scalar(select(func.count()).select_from(User)) == 1


async def test_a_known_sub_whose_address_changed_keeps_the_account(session: AsyncSession) -> None:
    """The subject is the stable identifier; a renamed mailbox is still the same reader. The
    address on file is left alone, because it is unique and the new one may belong elsewhere."""
    instance = await _create_instance(session, oidc_issuer="https://idp.example.com")
    first = await get_or_create_sso_user(
        session, instance, sub="stable-subject", email="before@example.com"
    )

    second = await get_or_create_sso_user(
        session, instance, sub="stable-subject", email="after@example.com"
    )

    assert second.id == first.id
    assert second.email == "before@example.com"
