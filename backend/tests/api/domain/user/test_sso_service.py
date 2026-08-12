from collections.abc import AsyncIterator

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from api.domain.user.exceptions import SsoNotConfiguredError
from api.domain.user.models import Instance
from api.domain.user.sso_service import ensure_sso_configured, get_or_create_sso_user
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
