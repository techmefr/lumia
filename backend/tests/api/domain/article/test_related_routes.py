from collections.abc import AsyncIterator
from datetime import UTC, datetime

import httpx
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from api.domain.article.models import Article, ArticleKeyword, Keyword, Lang
from api.domain.feed.models import Feed, SourceType
from api.domain.recommendation.bulk_feedback_service import FeedbackAxis, set_feedback_axis
from api.domain.recommendation.related_service import refresh_related_articles
from api.domain.user.models import User
from api.main import app
from api.technical.auth.jwt import create_access_token
from config.database import get_engine

ADMIN_PAYLOAD = {
    "email": "admin@example.com",
    "username": "admin",
    "password": "correct-horse-battery-staple",
}


@pytest.fixture
async def client(db_schema: None) -> AsyncIterator[httpx.AsyncClient]:
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as async_client:
        yield async_client


async def _headers(client: httpx.AsyncClient) -> dict[str, str]:
    response = await client.post("/onboarding/admin", json=ADMIN_PAYLOAD)
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def _feed(user: User, external_feed_id: str) -> Feed:
    return Feed(
        user_id=user.id,
        source_type=SourceType.MINIFLUX,
        external_feed_id=external_feed_id,
        title=f"Feed {external_feed_id}",
        url=f"https://example.com/{external_feed_id}/feed",
    )


async def _article_with_keywords(
    session: AsyncSession, feed: Feed, *, external_entry_id: str, terms: list[str], day: int = 1
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
    return article


async def test_an_article_with_no_related_content_returns_an_empty_list(
    client: httpx.AsyncClient,
) -> None:
    headers = await _headers(client)
    session_factory = async_sessionmaker(get_engine(), expire_on_commit=False)
    async with session_factory() as session:
        user = (await session.scalars(select(User))).one()
        feed = _feed(user, "10")
        session.add(feed)
        await session.flush()
        article = await _article_with_keywords(
            session, feed, external_entry_id="1", terms=["solo"]
        )
        await session.commit()
        article_id = article.id

    response = await client.get(f"/articles/{article_id}/related", headers=headers)

    assert response.status_code == 200
    assert response.json() == []


async def test_related_articles_are_returned_in_score_order(client: httpx.AsyncClient) -> None:
    headers = await _headers(client)
    session_factory = async_sessionmaker(get_engine(), expire_on_commit=False)
    async with session_factory() as session:
        user = (await session.scalars(select(User))).one()
        feed = _feed(user, "10")
        session.add(feed)
        await session.flush()
        source = await _article_with_keywords(
            session, feed, external_entry_id="1", terms=["ia", "python"], day=1
        )
        strong_match = await _article_with_keywords(
            session, feed, external_entry_id="2", terms=["ia", "python"], day=2
        )
        weak_match = await _article_with_keywords(
            session, feed, external_entry_id="3", terms=["ia"], day=20
        )
        await session.commit()
        await refresh_related_articles(session, source, user.id)
        await session.commit()
        article_id = source.id

    response = await client.get(f"/articles/{article_id}/related", headers=headers)

    assert response.status_code == 200
    ids = [article["id"] for article in response.json()]
    assert ids == [str(strong_match.id), str(weak_match.id)]


async def test_an_already_read_related_article_is_excluded(client: httpx.AsyncClient) -> None:
    headers = await _headers(client)
    session_factory = async_sessionmaker(get_engine(), expire_on_commit=False)
    async with session_factory() as session:
        user = (await session.scalars(select(User))).one()
        feed = _feed(user, "10")
        session.add(feed)
        await session.flush()
        source = await _article_with_keywords(
            session, feed, external_entry_id="1", terms=["ia"], day=1
        )
        already_read = await _article_with_keywords(
            session, feed, external_entry_id="2", terms=["ia"], day=2
        )
        await session.commit()
        await refresh_related_articles(session, source, user.id)
        await set_feedback_axis(
            session, user.id, [already_read.id], axis=FeedbackAxis.READ, value=True
        )
        await session.commit()
        article_id = source.id

    response = await client.get(f"/articles/{article_id}/related", headers=headers)

    assert response.status_code == 200
    assert response.json() == []


async def test_a_reader_never_sees_another_users_related_articles(
    client: httpx.AsyncClient,
) -> None:
    await _headers(client)
    session_factory = async_sessionmaker(get_engine(), expire_on_commit=False)
    async with session_factory() as session:
        user = (await session.scalars(select(User))).one()
        feed = _feed(user, "10")
        session.add(feed)
        await session.flush()
        source = await _article_with_keywords(
            session, feed, external_entry_id="1", terms=["ia"], day=1
        )
        await session.commit()
        await refresh_related_articles(session, source, user.id)
        await session.commit()
        article_id = source.id

        other = User(
            instance_id=user.instance_id,
            email="other@example.com",
            username="other",
            password_hash=None,
        )
        session.add(other)
        await session.commit()
        other_id = other.id

    other_headers = {"Authorization": f"Bearer {create_access_token(other_id)}"}

    response = await client.get(f"/articles/{article_id}/related", headers=other_headers)

    assert response.status_code == 404
