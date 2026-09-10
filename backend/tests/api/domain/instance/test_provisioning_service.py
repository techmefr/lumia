from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from api.domain.instance.provisioning_service import provision_admin_from_env
from api.domain.user.models import Instance, Role, User
from config.instance import InstanceConfig

ENV = InstanceConfig(
    admin_email="patron@example.com",
    admin_username="patron",
    admin_password="correct-horse-battery-staple",
    max_accounts=3,
    account_quota_mb=250,
)


async def test_without_the_admin_variables_nothing_is_provisioned(session: AsyncSession) -> None:
    created = await provision_admin_from_env(session, InstanceConfig())

    assert created is None
    assert await session.scalar(select(func.count()).select_from(Instance)) == 0


async def test_the_admin_and_the_instance_come_from_the_environment(
    session: AsyncSession,
) -> None:
    admin = await provision_admin_from_env(session, ENV)

    assert admin is not None
    assert admin.role == Role.ADMIN
    assert admin.email == ENV.admin_email
    assert admin.password_hash is not None
    instance = await session.scalar(select(Instance))
    assert instance is not None
    assert (instance.max_accounts, instance.disk_quota_mb) == (3, 250)


async def test_a_restart_creates_no_second_admin_and_keeps_the_password(
    session: AsyncSession,
) -> None:
    first = await provision_admin_from_env(session, ENV)
    assert first is not None
    stored_hash = first.password_hash

    changed = InstanceConfig(
        admin_email=ENV.admin_email,
        admin_username=ENV.admin_username,
        admin_password="a-completely-different-password",
        max_accounts=99,
        account_quota_mb=9999,
    )
    assert await provision_admin_from_env(session, changed) is None

    assert await session.scalar(select(func.count()).select_from(User)) == 1
    admin = await session.scalar(select(User))
    assert admin is not None
    assert admin.password_hash == stored_hash
    instance = await session.scalar(select(Instance))
    assert instance is not None
    assert (instance.max_accounts, instance.disk_quota_mb) == (3, 250)


async def test_an_instance_onboarded_from_the_browser_is_left_alone(
    session: AsyncSession,
) -> None:
    instance = Instance(max_accounts=10, disk_quota_mb=1000)
    session.add(instance)
    await session.flush()
    session.add(
        User(
            instance_id=instance.id,
            email="deja@example.com",
            username="deja",
            role=Role.ADMIN,
        )
    )
    await session.commit()

    assert await provision_admin_from_env(session, ENV) is None
    assert await session.scalar(select(func.count()).select_from(User)) == 1
