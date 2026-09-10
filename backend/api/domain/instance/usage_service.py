from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import ColumnElement, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from api.domain.article.models import Article
from api.domain.feed.models import Feed
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


def _stored_bytes_expression() -> ColumnElement[int]:
    """What an account actually occupies: the text of the articles kept under its own feeds.

    Articles are stored per feed and a feed belongs to exactly one account, so nothing here is
    shared between accounts and no reader is charged for another's library. Enriched content and
    summaries are the two columns that grow without bound; the rest of a row is fixed overhead.
    """
    return func.coalesce(
        func.sum(
            func.octet_length(Article.content)
            + func.octet_length(func.coalesce(Article.summary, ""))
        ),
        0,
    )


async def get_account_used_bytes(session: AsyncSession, user_id: UUID) -> int:
    used = await session.scalar(
        select(_stored_bytes_expression())
        .select_from(Article)
        .join(Feed, Feed.id == Article.feed_id)
        .where(Feed.user_id == user_id)
    )
    return int(used or 0)


async def list_account_usages(session: AsyncSession) -> list[AccountUsage]:
    """Every account with what it stores, in one grouped query rather than one query per account."""
    rows = await session.execute(
        select(
            User.id,
            User.email,
            User.username,
            User.role,
            _stored_bytes_expression(),
        )
        .select_from(User)
        .outerjoin(Feed, Feed.user_id == User.id)
        .outerjoin(Article, Article.feed_id == Feed.id)
        .group_by(User.id, User.email, User.username, User.role)
        .order_by(User.email)
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


async def ensure_within_disk_quota(session: AsyncSession, instance: Instance, user: User) -> None:
    used_bytes = await get_account_used_bytes(session, user.id)
    quota_bytes = instance.disk_quota_mb * BYTES_PER_MB
    if used_bytes >= quota_bytes:
        raise AccountQuotaExceededError(
            used_mb=used_bytes // BYTES_PER_MB, quota_mb=instance.disk_quota_mb
        )
