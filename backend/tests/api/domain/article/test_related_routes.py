from collections.abc import AsyncIterator
from datetime import UTC, datetime
from uuid import UUID, uuid4

import httpx
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker

from api.domain.article.models import Article, ArticleKeyword, Keyword, Lang
from api.domain.feed.models import Feed, SourceType
from api.domain.recommendation.models import UserArticleFeedback
from api.domain.user.models import User
from api.main import app
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


def _article(feed: Feed, name: str, url: str | None = None) -> Article:
    return Article(
        feed_id=feed.id,
        external_entry_id=name,
        title=name,
        url=url or f"https://example.com/{name}",
        content="body",
        published_at=datetime(2026, 8, 12, tzinfo=UTC),
    )


def _feed(user: User, key: str) -> Feed:
    return Feed(
        user_id=user.id,
        source_type=SourceType.MINIFLUX,
        external_feed_id=key,
        title=key,
        url=f"https://example.com/feed-{key}",
    )


async def _seed() -> dict[str, UUID]:
    factory = async_sessionmaker(get_engine(), expire_on_commit=False)
    async with factory() as session:
        user = (await session.scalars(select(User))).one()
        stranger = User(
            instance_id=user.instance_id, email="o@example.com", username="other", password_hash="x"
        )
        session.add(stranger)
        await session.flush()
        feed = _feed(user, "own")
        foreign_feed = _feed(stranger, "foreign")
        mirror_feed = _feed(user, "mirror")
        session.add_all([feed, foreign_feed, mirror_feed])
        await session.flush()
        names = ["main", "close", "far", "read", "dupe", "unrelated"]
        articles = {
            name: (
                _article(mirror_feed, name, "https://example.com/main")
                if name == "dupe"
                else _article(feed, name)
            )
            for name in names
        }
        articles["foreign"] = _article(foreign_feed, "foreign")
        session.add_all(articles.values())
        python = Keyword(term="python", lang=Lang.EN)
        rss = Keyword(term="rss", lang=Lang.EN)
        session.add_all([python, rss])
        await session.flush()
        links = [
            ("main", python, 1.0),
            ("main", rss, 1.0),
            ("close", python, 0.9),
            ("close", rss, 0.9),
            ("far", rss, 0.2),
            ("read", python, 1.0),
            ("dupe", python, 1.0),
            ("foreign", python, 1.0),
        ]
        session.add_all(
            ArticleKeyword(article_id=articles[name].id, keyword_id=keyword.id, weight=weight)
            for name, keyword, weight in links
        )
        session.add(UserArticleFeedback(user_id=user.id, article_id=articles["read"].id, read=True))
        await session.commit()
        return {name: article.id for name, article in articles.items()}


async def test_related_articles_are_ranked_by_shared_keywords(client: httpx.AsyncClient) -> None:
    headers = await _headers(client)
    ids = await _seed()

    response = await client.get(f"/articles/{ids['main']}/related", headers=headers)

    assert response.status_code == 200
    assert [item["id"] for item in response.json()] == [str(ids["close"]), str(ids["far"])]


async def test_read_duplicate_foreign_and_unrelated_articles_are_left_out(
    client: httpx.AsyncClient,
) -> None:
    headers = await _headers(client)
    ids = await _seed()

    response = await client.get(f"/articles/{ids['main']}/related", headers=headers)

    returned = {item["id"] for item in response.json()}
    for name in ("read", "dupe", "foreign", "unrelated", "main"):
        assert str(ids[name]) not in returned


async def test_a_foreign_or_missing_article_is_a_404(client: httpx.AsyncClient) -> None:
    headers = await _headers(client)
    ids = await _seed()

    foreign = await client.get(f"/articles/{ids['foreign']}/related", headers=headers)
    missing = await client.get(f"/articles/{uuid4()}/related", headers=headers)

    assert foreign.status_code == 404
    assert missing.status_code == 404
