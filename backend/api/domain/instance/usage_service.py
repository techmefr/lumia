from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.domain.instance.exceptions import AccountQuotaExceededError
from api.domain.user.models import Instance, Role, User

BYTES_PER_MB = 1024 * 1024


@dataclass(frozen=True)
class AccountUsage:
    user_id: UUID
    email: str
    username: str
    role: Role
    used_bytes: int

    @property
    def used_mb(self) -> int:
        return self.used_bytes // BYTES_PER_MB


async def get_account_used_bytes(session: AsyncSession, user_id: UUID) -> int:
    used = await session.scalar(select(User.stored_bytes).where(User.id == user_id))
    return int(used or 0)


async def list_account_usages(session: AsyncSession) -> list[AccountUsage]:
    rows = await session.execute(
        select(User.id, User.email, User.username, User.role, User.stored_bytes).order_by(
            User.email
        )
    )
    return [
        AccountUsage(
            user_id=row[0],
            email=row[1],
            username=row[2],
            role=row[3],
            used_bytes=int(row[4] or 0),
        )
        for row in rows
    ]


async def has_disk_quota_room(session: AsyncSession, instance: Instance, user_id: UUID) -> bool:
    """Whether the account may still be given storage, for callers that skip instead of failing.

    Feed ingestion runs with nobody to tell: an over-quota reader keeps its library and its feeds,
    new entries simply stop being stored until it makes room.
    """
    used_bytes = await get_account_used_bytes(session, user_id)
    return used_bytes < instance.disk_quota_mb * BYTES_PER_MB


async def ensure_within_disk_quota(session: AsyncSession, instance: Instance, user: User) -> None:
    used_bytes = await get_account_used_bytes(session, user.id)
    quota_bytes = instance.disk_quota_mb * BYTES_PER_MB
    if used_bytes >= quota_bytes:
        raise AccountQuotaExceededError(
            used_mb=used_bytes // BYTES_PER_MB, quota_mb=instance.disk_quota_mb
        )
