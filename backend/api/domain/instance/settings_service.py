from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.domain.instance.capacity_service import count_accounts
from api.domain.instance.exceptions import (
    InstanceNotProvisionedError,
    MaxAccountsBelowCurrentCountError,
)
from api.domain.instance.models import AccessMode
from api.domain.user.models import Instance


async def get_instance(session: AsyncSession) -> Instance:
    instance = await session.scalar(select(Instance))
    if instance is None:
        raise InstanceNotProvisionedError
    return instance


async def update_instance_settings(
    session: AsyncSession,
    instance: Instance,
    *,
    max_accounts: int | None = None,
    disk_quota_mb: int | None = None,
    access_mode: AccessMode | None = None,
) -> Instance:
    """Applies the admin's new numbers, refusing a cap the instance is already past.

    Lowering `max_accounts` under the number of accounts that exist would leave the instance in a
    state no code path can repair — every check would read as full — so it is refused rather than
    stored and worked around later.
    """
    if max_accounts is not None:
        if max_accounts < await count_accounts(session):
            raise MaxAccountsBelowCurrentCountError
        instance.max_accounts = max_accounts
    if disk_quota_mb is not None:
        instance.disk_quota_mb = disk_quota_mb
    if access_mode is not None:
        instance.access_mode = access_mode
    await session.commit()
    return instance
