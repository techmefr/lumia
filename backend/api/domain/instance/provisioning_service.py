import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.domain.user.models import Instance, Role, User
from api.technical.auth.hashing import hash_password
from config.instance import InstanceConfig, get_instance_config

logger = logging.getLogger(__name__)


async def provision_admin_from_env(
    session: AsyncSession, config: InstanceConfig | None = None
) -> User | None:
    """Creates the instance and its admin account from the environment, once.

    Idempotent by design: a restart with the same variables finds an admin already there and
    changes nothing — in particular it never rewrites a password the admin may have changed since.
    Returns the account it created, or None when there was nothing to do.
    """
    settings = config or get_instance_config()
    if not (settings.admin_email and settings.admin_username and settings.admin_password):
        return None

    existing_admin = await session.scalar(select(User).where(User.role == Role.ADMIN))
    if existing_admin is not None:
        return None

    instance = await session.scalar(select(Instance))
    if instance is None:
        instance = Instance(
            max_accounts=settings.max_accounts,
            disk_quota_mb=settings.account_quota_mb,
        )
        session.add(instance)
        await session.flush()

    admin = User(
        instance_id=instance.id,
        email=settings.admin_email,
        username=settings.admin_username,
        password_hash=hash_password(settings.admin_password),
        role=Role.ADMIN,
    )
    session.add(admin)
    await session.commit()
    logger.info("provisioned the instance admin account from the environment")
    return admin
