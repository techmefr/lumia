from collections.abc import AsyncIterator
from datetime import UTC, datetime

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from api.domain.article.models import Article, ArticleKeyword, Keyword, Lang
from api.domain.feed.models import Feed, SourceType
from api.domain.recommendation.related_service import fetch_related, refresh_related_articles
from api.domain.user.models import Instance, User
from config.database import get_engine


@pytest.fixture
async def session(db_schema: None) -> AsyncIterator[AsyncSession]:
    session_factory = async_sessionmaker(get_engine(), expire_on_commit=False)
    async with session_factory() as db_session:
        yield db_session


async def _user_and_feed(session: AsyncSession, *, external_feed_id: str = "10") -> tuple[User, Feed]:
    instance = Instance(max_accounts=10, disk_quota_mb=1000)
    session.add(instance)
    await session.flush()
    user = User(
        instance_id=instance.id,
        email=f"user-{external_feed_id}@example.com",
        username=f"user-{external_feed_id}",
        password_hash=None,
    )
    session.add(user)
    await session.flush()
    feed = Feed(
        user_id=user.id,
        source_type=SourceType.MINIFLUX,
        external_feed_id=external_feed_id,
        title="Feed",
        url=f"https://example.com/{external_feed_id}/feed",
    )
    session.add(feed)
    await session.commit()
    return user, feed


async def _article_with_keywords(
    session: AsyncSession,
    feed: Feed,
    *,
    external_entry_id: str,
    terms: list[str],
    day: int = 1,
) -> Article:
    article = Article(
        feed_id=feed.id,
        external_entry_id=external_entry_id,
        title=f"Article {external_entry_id}",
        url=f"https://example.com/{external_entry_id}",
        content="Content",
        published_at=datetime(2026, 8, day, tzinfo=UTC),
    )
    session.add(article)
    await session.flush()
    for term in terms:
        keyword = Keyword(term=term, lang=Lang.FR)
        session.add(keyword)
        await session.flush()
        session.add(ArticleKeyword(article_id=article.id, keyword_id=keyword.id, weight=1.0))
    await session.commit()
    return article


async def test_articles_sharing_keywords_become_related(session: AsyncSession) -> None:
    user, feed = await _user_and_feed(session)
    source = await _article_with_keywords(session, feed, external_entry_id="1", terms=["ia", "python"])
    match = await _article_with_keywords(session, feed, external_entry_id="2", terms=["ia", "rust"])
    unrelated = await _article_with_keywords(session, feed, external_entry_id="3", terms=["cuisine"])

    await refresh_related_articles(session, source, user.id)
    await session.commit()

    related = await fetch_related(session, user.id, source.id, limit=10)

    assert [article.id for article in related] == [match.id]
    assert unrelated.id not in [article.id for article in related]


async def test_an_article_with_no_shared_keyword_has_no_related_articles(
    session: AsyncSession,
) -> None:
    user, feed = await _user_and_feed(session)
    lonely = await _article_with_keywords(session, feed, external_entry_id="1", terms=["solo"])

    await refresh_related_articles(session, lonely, user.id)
    await session.commit()

    related = await fetch_related(session, user.id, lonely.id, limit=10)

    assert related == []


async def test_a_new_article_refreshes_the_neighbour_it_matched(session: AsyncSession) -> None:
    user, feed = await _user_and_feed(session)
    first = await _article_with_keywords(session, feed, external_entry_id="1", terms=["ia"], day=1)
    await refresh_related_articles(session, first, user.id)
    await session.commit()
    assert await fetch_related(session, user.id, first.id, limit=10) == []

    second = await _article_with_keywords(session, feed, external_entry_id="2", terms=["ia"], day=2)
    await refresh_related_articles(session, second, user.id)
    await session.commit()

    related_to_first = await fetch_related(session, user.id, first.id, limit=10)
    assert [article.id for article in related_to_first] == [second.id]


async def test_related_articles_never_cross_a_user_boundary(session: AsyncSession) -> None:
    owner, owner_feed = await _user_and_feed(session, external_feed_id="10")
    _other, other_feed = await _user_and_feed(session, external_feed_id="20")
    source = await _article_with_keywords(session, owner_feed, external_entry_id="1", terms=["ia"])
    await _article_with_keywords(session, other_feed, external_entry_id="2", terms=["ia"])

    await refresh_related_articles(session, source, owner.id)
    await session.commit()

    related = await fetch_related(session, owner.id, source.id, limit=10)

    assert related == []
