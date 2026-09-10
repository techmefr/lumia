from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from api.domain.instance.exceptions import InstanceFullError
from api.domain.user.models import Instance, User


async def count_accounts(session: AsyncSession) -> int:
    return await session.scalar(select(func.count()).select_from(User)) or 0


async def ensure_instance_has_room(session: AsyncSession, instance: Instance) -> None:
    if await count_accounts(session) >= instance.max_accounts:
        raise InstanceFullError
