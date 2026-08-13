from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.domain.article.models import Article, Author
from api.domain.feed.models import Feed, SourceType
from api.domain.recommendation.models import UserArticleFeedback
from api.domain.user.models import User
from worker.technical.content_extraction import PageExtractor, TrafilaturaPageExtractor

MANUAL_FEED_TITLE = "Enregistrés"
_MANUAL_EXTERNAL_ID = "manual"


async def save_url(
    session: AsyncSession,
    user: User,
    url: str,
    *,
    page_extractor: PageExtractor | None = None,
) -> Article:
    """Saves an arbitrary web page as a readable article on the user's manual feed.

    Re-saving a URL already saved returns the existing article rather than duplicating it, so the
    reading list stays clean when the same link arrives twice.
    """
    feed = await _get_or_create_manual_feed(session, user)

    existing = await session.scalar(
        select(Article).where(Article.feed_id == feed.id, Article.url == url)
    )
    if existing is not None:
        await _mark_saved(session, user, existing)
        return await _reload(session, existing)

    extractor = page_extractor or TrafilaturaPageExtractor()
    page = await extractor.fetch(url)

    author_id: UUID | None = None
    if page.author:
        author_id = await _get_or_create_author(session, page.author)

    article = Article(
        feed_id=feed.id,
        author_id=author_id,
        external_entry_id=url,
        title=page.title,
        url=url,
        content=page.content,
        image_url=page.image_url,
        published_at=page.published_at or datetime.now(UTC),
    )
    session.add(article)
    await session.flush()
    await _mark_saved(session, user, article)
    return await _reload(session, article)


async def _reload(session: AsyncSession, article: Article) -> Article:
    """Loads the article's relationships explicitly — a freshly inserted instance has none of them
    populated, and touching one afterwards would trigger a lazy load under asyncio."""
    await session.refresh(article, ["feed", "author", "category", "keyword_links"])
    return article


async def _get_or_create_manual_feed(session: AsyncSession, user: User) -> Feed:
    feed = await session.scalar(
        select(Feed).where(Feed.user_id == user.id, Feed.source_type == SourceType.MANUAL)
    )
    if feed is None:
        feed = Feed(
            user_id=user.id,
            source_type=SourceType.MANUAL,
            external_feed_id=_MANUAL_EXTERNAL_ID,
            title=MANUAL_FEED_TITLE,
            url="",
        )
        session.add(feed)
        await session.flush()
    return feed


async def _get_or_create_author(session: AsyncSession, name: str) -> UUID:
    author = await session.scalar(select(Author).where(Author.name == name))
    if author is None:
        author = Author(name=name)
        session.add(author)
        await session.flush()
    return author.id


async def _mark_saved(session: AsyncSession, user: User, article: Article) -> None:
    feedback = await session.scalar(
        select(UserArticleFeedback).where(
            UserArticleFeedback.user_id == user.id,
            UserArticleFeedback.article_id == article.id,
        )
    )
    if feedback is None:
        feedback = UserArticleFeedback(user_id=user.id, article_id=article.id)
        session.add(feedback)
    feedback.saved = True
    await session.commit()
