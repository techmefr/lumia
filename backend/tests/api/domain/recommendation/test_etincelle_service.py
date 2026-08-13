from collections.abc import AsyncIterator
from datetime import UTC, datetime

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from api.domain.article.models import Article, ArticleKeyword, Author, Category, Keyword, Lang
from api.domain.feed.models import Feed, SourceType
from api.domain.recommendation.etincelle_service import list_etincelle
from api.domain.recommendation.models import UserArticleFeedback, UserFeedScore, Vote
from api.domain.user.models import Instance, User
from config.database import get_engine


@pytest.fixture
async def session(db_schema: None) -> AsyncIterator[AsyncSession]:
    session_factory = async_sessionmaker(get_engine(), expire_on_commit=False)
    async with session_factory() as db_session:
        yield db_session


async def _create_user_and_feed(session: AsyncSession) -> tuple[User, Feed]:
    instance = Instance(max_accounts=10, disk_quota_mb=1000)
    session.add(instance)
    await session.flush()
    user = User(
        instance_id=instance.id, email="user@example.com", username="user", password_hash=None
    )
    session.add(user)
    await session.flush()
    feed = Feed(
        user_id=user.id,
        source_type=SourceType.MINIFLUX,
        external_feed_id="10",
        title="Feed",
        url="https://example.com/feed",
    )
    session.add(feed)
    await session.commit()
    return user, feed


async def _create_article(session: AsyncSession, feed: Feed, *, external_entry_id: str) -> Article:
    article = Article(
        feed_id=feed.id,
        external_entry_id=external_entry_id,
        title=f"Article {external_entry_id}",
        url=f"https://example.com/{external_entry_id}",
        content="Content",
        published_at=datetime(2026, 8, 12, tzinfo=UTC),
    )
    session.add(article)
    await session.commit()
    return article


async def test_list_etincelle_excludes_articles_already_voted(session: AsyncSession) -> None:
    user, feed = await _create_user_and_feed(session)
    voted = await _create_article(session, feed, external_entry_id="1")
    unvoted = await _create_article(session, feed, external_entry_id="2")
    session.add(UserArticleFeedback(user_id=user.id, article_id=voted.id, sentiment=Vote.LIKE))
    await session.commit()

    ranked = await list_etincelle(session, user.id)

    ranked_ids = [article.id for article, _ in ranked]
    assert unvoted.id in ranked_ids
    assert voted.id not in ranked_ids


async def test_list_etincelle_orders_by_descending_average_score(session: AsyncSession) -> None:
    user, feed = await _create_user_and_feed(session)
    low = await _create_article(session, feed, external_entry_id="1")
    high = await _create_article(session, feed, external_entry_id="2")

    other_feed = Feed(
        user_id=user.id,
        source_type=SourceType.MINIFLUX,
        external_feed_id="20",
        title="Other feed",
        url="https://example.com/other-feed",
    )
    session.add(other_feed)
    await session.flush()
    high.feed_id = other_feed.id
    session.add(UserFeedScore(user_id=user.id, feed_id=other_feed.id, score=2.0))
    session.add(UserFeedScore(user_id=user.id, feed_id=feed.id, score=-1.0))
    await session.commit()

    ranked = await list_etincelle(session, user.id)

    ranked_ids = [article.id for article, _ in ranked]
    assert ranked_ids.index(high.id) < ranked_ids.index(low.id)


async def test_list_etincelle_treats_missing_scores_as_zero(session: AsyncSession) -> None:
    user, feed = await _create_user_and_feed(session)
    author = Author(name="Jane Doe")
    session.add(author)
    await session.flush()
    article = await _create_article(session, feed, external_entry_id="1")
    article.author_id = author.id
    keyword = Keyword(term="chat", lang=Lang.FR)
    category = Category(name="Tech")
    session.add_all([keyword, category])
    await session.flush()
    article.category_id = category.id
    session.add(ArticleKeyword(article_id=article.id, keyword_id=keyword.id, weight=0.5))
    await session.commit()

    ranked = await list_etincelle(session, user.id)

    assert ranked == [(article, 0.0)]
