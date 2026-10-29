from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import InstrumentedAttribute

from api.domain.article.models import Article, ArticleKeyword, ArticleShare
from api.domain.audio.models import ArticleAudio
from api.domain.chat.models import ChatMessage
from api.domain.export.models import ExportJob
from api.domain.feed.models import Feed, Folder
from api.domain.fever.models import FeverKey
from api.domain.highlight.models import Highlight
from api.domain.newsletter.models import NewsletterInbox
from api.domain.playlist.models import Playlist, PlaylistItem, PlaylistMember
from api.domain.recommendation.models import (
    UserArticleFeedback,
    UserAuthorScore,
    UserCategoryScore,
    UserFeedScore,
    UserFilterRule,
    UserKeywordScore,
)
from api.domain.saved_search.models import AlertNotification, SavedSearch
from api.domain.tag.models import ArticleTag, Tag
from api.domain.user.exceptions import LastAdminError
from api.domain.user.models import MagicLinkToken, RecoveryCode, RefreshToken, Role, User
from api.technical.batching import chunked


async def delete_account(session: AsyncSession, user_id: UUID) -> None:
    """Erases an account and everything that belongs to it.

    The cascade is written out rather than left to the database: no foreign key in this schema
    declares one, so a plain DELETE on the user would fail on the first reference and a hidden
    ON DELETE added later would decide the order for us. Written here, the order is the one the
    domain wants — the rows that point at articles go before the articles themselves.
    """
    await _refuse_to_orphan_the_instance(session, user_id)
    await session.execute(delete(ExportJob).where(ExportJob.user_id == user_id))

    feed_ids = list(await session.scalars(select(Feed.id).where(Feed.user_id == user_id)))
    article_ids: list[UUID] = []
    for feed_batch in chunked(feed_ids):
        article_ids.extend(
            await session.scalars(select(Article.id).where(Article.feed_id.in_(feed_batch)))
        )
    tag_ids = list(await session.scalars(select(Tag.id).where(Tag.user_id == user_id)))
    playlist_ids = list(
        await session.scalars(select(Playlist.id).where(Playlist.user_id == user_id))
    )

    await session.execute(delete(AlertNotification).where(AlertNotification.user_id == user_id))
    await session.execute(delete(SavedSearch).where(SavedSearch.user_id == user_id))
    await _delete_where_in(session, PlaylistItem.playlist_id, playlist_ids)
    await _delete_where_in(session, PlaylistItem.article_id, article_ids)
    await session.execute(delete(Highlight).where(Highlight.user_id == user_id))
    await _delete_where_in(session, Highlight.article_id, article_ids)
    await session.execute(
        update(PlaylistItem)
        .where(PlaylistItem.added_by_user_id == user_id)
        .values(added_by_user_id=None)
    )
    await _delete_where_in(session, PlaylistMember.playlist_id, playlist_ids)
    await session.execute(delete(PlaylistMember).where(PlaylistMember.user_id == user_id))
    await _delete_where_in(session, ArticleTag.tag_id, tag_ids)
    await _delete_where_in(session, ArticleTag.article_id, article_ids)
    await _delete_where_in(session, Tag.id, tag_ids)
    await session.execute(delete(UserArticleFeedback).where(UserArticleFeedback.user_id == user_id))
    await _delete_where_in(session, UserArticleFeedback.article_id, article_ids)
    await session.execute(delete(ArticleShare).where(ArticleShare.user_id == user_id))
    await _delete_where_in(session, ArticleShare.article_id, article_ids)
    await session.execute(delete(NewsletterInbox).where(NewsletterInbox.user_id == user_id))
    await _delete_where_in(session, ArticleKeyword.article_id, article_ids)
    await session.execute(delete(ArticleAudio).where(ArticleAudio.user_id == user_id))
    await _delete_where_in(session, ArticleAudio.article_id, article_ids)
    await session.execute(delete(ChatMessage).where(ChatMessage.user_id == user_id))
    await _delete_where_in(session, ChatMessage.article_id, article_ids)
    await _delete_where_in(session, Article.id, article_ids)

    await session.execute(delete(UserFeedScore).where(UserFeedScore.user_id == user_id))
    await session.execute(delete(UserKeywordScore).where(UserKeywordScore.user_id == user_id))
    await session.execute(delete(UserAuthorScore).where(UserAuthorScore.user_id == user_id))
    await session.execute(delete(UserCategoryScore).where(UserCategoryScore.user_id == user_id))
    await session.execute(delete(UserFilterRule).where(UserFilterRule.user_id == user_id))

    await _delete_where_in(session, Playlist.id, playlist_ids)
    await _delete_where_in(session, Feed.id, feed_ids)
    await session.execute(delete(Folder).where(Folder.user_id == user_id))

    await session.execute(delete(FeverKey).where(FeverKey.user_id == user_id))
    await session.execute(delete(RecoveryCode).where(RecoveryCode.user_id == user_id))
    await session.execute(delete(RefreshToken).where(RefreshToken.user_id == user_id))
    await session.execute(delete(MagicLinkToken).where(MagicLinkToken.user_id == user_id))
    await session.execute(delete(User).where(User.id == user_id))
    await session.commit()


async def _delete_where_in(
    session: AsyncSession, column: InstrumentedAttribute[UUID], ids: Sequence[UUID]
) -> None:
    for batch in chunked(ids):
        await session.execute(delete(column.class_).where(column.in_(batch)))


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
