from uuid import UUID

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from api.domain.article.models import Article, ArticleKeyword
from api.domain.feed.models import Feed, Folder
from api.domain.playlist.models import Playlist, PlaylistItem
from api.domain.recommendation.models import (
    UserArticleFeedback,
    UserAuthorScore,
    UserCategoryScore,
    UserFeedScore,
    UserFilterRule,
    UserKeywordScore,
)
from api.domain.user.exceptions import LastAdminError
from api.domain.user.models import MagicLinkToken, RefreshToken, Role, User


async def delete_account(session: AsyncSession, user_id: UUID) -> None:
    """Erases an account and everything that belongs to it.

    The cascade is written out rather than left to the database: no foreign key in this schema
    declares one, so a plain DELETE on the user would fail on the first reference and a hidden
    ON DELETE added later would decide the order for us. Written here, the order is the one the
    domain wants — the rows that point at articles go before the articles themselves.
    """
    await _refuse_to_orphan_the_instance(session, user_id)

    feed_ids = list(await session.scalars(select(Feed.id).where(Feed.user_id == user_id)))
    article_ids = list(
        await session.scalars(select(Article.id).where(Article.feed_id.in_(feed_ids)))
    )
    playlist_ids = list(
        await session.scalars(select(Playlist.id).where(Playlist.user_id == user_id))
    )

    await session.execute(
        delete(PlaylistItem).where(
            PlaylistItem.playlist_id.in_(playlist_ids) | PlaylistItem.article_id.in_(article_ids)
        )
    )
    await session.execute(
        delete(UserArticleFeedback).where(
            (UserArticleFeedback.user_id == user_id)
            | UserArticleFeedback.article_id.in_(article_ids)
        )
    )
    await session.execute(delete(ArticleKeyword).where(ArticleKeyword.article_id.in_(article_ids)))
    await session.execute(delete(Article).where(Article.id.in_(article_ids)))

    await session.execute(delete(UserFeedScore).where(UserFeedScore.user_id == user_id))
    await session.execute(delete(UserKeywordScore).where(UserKeywordScore.user_id == user_id))
    await session.execute(delete(UserAuthorScore).where(UserAuthorScore.user_id == user_id))
    await session.execute(delete(UserCategoryScore).where(UserCategoryScore.user_id == user_id))
    await session.execute(delete(UserFilterRule).where(UserFilterRule.user_id == user_id))

    await session.execute(delete(Playlist).where(Playlist.id.in_(playlist_ids)))
    await session.execute(delete(Feed).where(Feed.id.in_(feed_ids)))
    await session.execute(delete(Folder).where(Folder.user_id == user_id))

    await session.execute(delete(RefreshToken).where(RefreshToken.user_id == user_id))
    await session.execute(delete(MagicLinkToken).where(MagicLinkToken.user_id == user_id))
    await session.execute(delete(User).where(User.id == user_id))
    await session.commit()


async def _refuse_to_orphan_the_instance(session: AsyncSession, user_id: UUID) -> None:
    """An instance with no admin left can never be administered again: onboarding is refused as
    soon as an instance exists, so there would be no way back."""
    user = await session.get(User, user_id)
    if user is None or user.role != Role.ADMIN:
        return
    remaining = await session.scalar(
        select(func.count())
        .select_from(User)
        .where(
            User.instance_id == user.instance_id,
            User.role == Role.ADMIN,
            User.id != user_id,
        )
    )
    if not remaining:
        raise LastAdminError
