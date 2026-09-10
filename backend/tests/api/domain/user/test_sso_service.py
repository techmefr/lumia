from collections.abc import AsyncIterator

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from api.domain.user.exceptions import SsoNotConfiguredError
from api.domain.user.models import Instance
from api.domain.user.sso_service import get_or_create_sso_user, read_sso_configuration
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


def _configured_instance(**overrides: str | None) -> Instance:
    settings: dict[str, str | None] = {
        "oidc_issuer": "https://idp.example.com",
        "oidc_client_id": "lumia",
        "oidc_client_secret_encrypted": "encrypted-secret",
        "oidc_redirect_uri": "https://lumia.example.com/auth/sso/callback",
    }
    settings.update(overrides)
    return Instance(max_accounts=10, disk_quota_mb=1000, **settings)


def test_reading_the_configuration_of_an_instance_without_sso_is_refused() -> None:
    with pytest.raises(SsoNotConfiguredError):
        read_sso_configuration(Instance(max_accounts=10, disk_quota_mb=1000))


@pytest.mark.parametrize(
    "missing",
    ["oidc_issuer", "oidc_client_id", "oidc_client_secret_encrypted", "oidc_redirect_uri"],
)
def test_a_half_configured_instance_is_refused_rather_than_carried_further(missing: str) -> None:
    with pytest.raises(SsoNotConfiguredError):
        read_sso_configuration(_configured_instance(**{missing: None}))


def test_a_fully_configured_instance_yields_its_four_settings() -> None:
    sso = read_sso_configuration(_configured_instance())

    assert sso.issuer == "https://idp.example.com"
    assert sso.client_id == "lumia"
    assert sso.client_secret_encrypted == "encrypted-secret"
    assert sso.redirect_uri == "https://lumia.example.com/auth/sso/callback"


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
