from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import select, text
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from api.domain.article.models import Article, Author
from api.domain.feed.models import MANUAL_FEED_PREDICATE, Feed, SourceType
from api.domain.recommendation.models import UserArticleFeedback
from api.domain.user.models import User
from api.technical.net.canonical_url import canonical_url
from worker.technical.content_extraction import PageExtractor, TrafilaturaPageExtractor

MANUAL_FEED_TITLE = "Enregistrés"
_MANUAL_EXTERNAL_ID = "manual"


async def find_saved_article(session: AsyncSession, user: User, url: str) -> Article | None:
    feed = await _get_or_create_manual_feed(session, user)
    existing: Article | None = await session.scalar(
        select(Article).where(
            Article.feed_id == feed.id, Article.canonical_url == canonical_url(url)
        )
    )
    return existing


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

    existing = await find_saved_article(session, user, url)
    if existing is not None:
        await _mark_saved(session, user, existing)
        return await _reload(session, existing)

    extractor = page_extractor or TrafilaturaPageExtractor()
    page = await extractor.fetch(url)

    await session.execute(select(Feed.id).where(Feed.id == feed.id).with_for_update())
    existing = await find_saved_article(session, user, url)
    if existing is not None:
        await _mark_saved(session, user, existing)
        return await _reload(session, existing)

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
    try:
        async with session.begin_nested():
            session.add(article)
    except IntegrityError:
        collided = await find_saved_article(session, user, url)
        if collided is None:
            raise
        await _mark_saved(session, user, collided)
        return await _reload(session, collided)
    await _mark_saved(session, user, article)
    return await _reload(session, article)


async def _reload(session: AsyncSession, article: Article) -> Article:
    """Loads the article's relationships explicitly — a freshly inserted instance has none of them
    populated, and touching one afterwards would trigger a lazy load under asyncio."""
    await session.refresh(article, ["feed", "author", "category", "keyword_links"])
    return article


async def _get_or_create_manual_feed(session: AsyncSession, user: User) -> Feed:
    await session.execute(
        pg_insert(Feed)
        .values(
            id=uuid4(),
            created_at=datetime.now(UTC),
            user_id=user.id,
            source_type=SourceType.MANUAL,
            external_feed_id=_MANUAL_EXTERNAL_ID,
            title=MANUAL_FEED_TITLE,
            url="",
        )
        .on_conflict_do_nothing(
            index_elements=[Feed.user_id], index_where=text(MANUAL_FEED_PREDICATE)
        )
    )
    feed = await session.scalar(
        select(Feed)
        .where(Feed.user_id == user.id, Feed.source_type == SourceType.MANUAL)
        .execution_options(populate_existing=True)
    )
    if feed is None:
        raise RuntimeError("manual feed missing right after its insert")
    return feed


async def _get_or_create_author(session: AsyncSession, name: str) -> UUID:
    await session.execute(
        pg_insert(Author)
        .values(id=uuid4(), name=name)
        .on_conflict_do_nothing(index_elements=[Author.name])
    )
    author = await session.scalar(select(Author).where(Author.name == name))
    if author is None:
        raise RuntimeError("author missing right after its insert")
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
