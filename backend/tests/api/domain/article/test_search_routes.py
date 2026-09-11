from collections.abc import AsyncIterator
from datetime import UTC, datetime

import httpx
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker

from api.domain.article.models import Article, Lang
from api.domain.feed.models import Feed, SourceType
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


async def _seed_searchable_articles() -> str:
    session_factory = async_sessionmaker(get_engine(), expire_on_commit=False)
    async with session_factory() as session:
        user = (await session.scalars(select(User))).one()
        feed = Feed(
            user_id=user.id,
            source_type=SourceType.MINIFLUX,
            external_feed_id="1",
            title="Feed",
            url="https://example.com/feed",
        )
        session.add(feed)
        await session.flush()
        session.add_all(
            [
                Article(
                    feed_id=feed.id,
                    external_entry_id="a",
                    title="Rust sort le borrow checker",
                    url="https://example.com/a",
                    content="Contenu quelconque",
                    published_at=datetime(2026, 8, 12, tzinfo=UTC),
                ),
                Article(
                    feed_id=feed.id,
                    external_entry_id="b",
                    title="Autre sujet",
                    url="https://example.com/b",
                    content="Ici on parle de kubernetes en detail",
                    summary="Un resume sur les clusters",
                    published_at=datetime(2026, 8, 11, tzinfo=UTC),
                ),
                Article(
                    feed_id=feed.id,
                    external_entry_id="c",
                    title="Sans rapport",
                    url="https://example.com/c",
                    content="Rien a voir",
                    published_at=datetime(2026, 8, 10, tzinfo=UTC),
                ),
            ]
        )
        await session.commit()
        return str(feed.id)


async def test_search_matches_the_title(client: httpx.AsyncClient) -> None:
    headers = await _headers(client)
    await _seed_searchable_articles()

    response = await client.get("/articles?q=borrow", headers=headers)
    assert [article["title"] for article in response.json()] == ["Rust sort le borrow checker"]


async def test_search_matches_the_content(client: httpx.AsyncClient) -> None:
    headers = await _headers(client)
    await _seed_searchable_articles()

    response = await client.get("/articles?q=kubernetes", headers=headers)
    assert [article["title"] for article in response.json()] == ["Autre sujet"]


async def test_search_matches_the_summary(client: httpx.AsyncClient) -> None:
    headers = await _headers(client)
    await _seed_searchable_articles()

    response = await client.get("/articles?q=clusters", headers=headers)
    assert [article["title"] for article in response.json()] == ["Autre sujet"]


async def test_search_is_case_insensitive(client: httpx.AsyncClient) -> None:
    headers = await _headers(client)
    await _seed_searchable_articles()

    response = await client.get("/articles?q=KUBERNETES", headers=headers)
    assert [article["title"] for article in response.json()] == ["Autre sujet"]


async def test_search_combines_with_the_feed_filter(client: httpx.AsyncClient) -> None:
    headers = await _headers(client)
    feed_id = await _seed_searchable_articles()

    response = await client.get(f"/articles?q=borrow&feed_id={feed_id}", headers=headers)
    assert len(response.json()) == 1

    other_feed = "00000000-0000-0000-0000-000000000000"
    empty = await client.get(f"/articles?q=borrow&feed_id={other_feed}", headers=headers)
    assert empty.json() == []


async def test_search_below_the_minimum_length_is_rejected(client: httpx.AsyncClient) -> None:
    headers = await _headers(client)
    response = await client.get("/articles?q=a", headers=headers)
    assert response.status_code == 422


async def test_search_stems_plural_forms(client: httpx.AsyncClient) -> None:
    """`websearch_to_tsquery` stems the query the same way the stored vector was stemmed, so a
    singular search term still reaches an article whose text only has the plural."""
    headers = await _headers(client)
    await _seed_searchable_articles()

    response = await client.get("/articles?q=cluster", headers=headers)
    assert [article["title"] for article in response.json()] == ["Autre sujet"]


async def test_search_never_reaches_another_users_articles(client: httpx.AsyncClient) -> None:
    await _headers(client)
    await _seed_searchable_articles()

    session_factory = async_sessionmaker(get_engine(), expire_on_commit=False)
    async with session_factory() as session:
        user = (await session.scalars(select(User))).one()
        other_user = User(
            instance_id=user.instance_id,
            email="other@example.com",
            username="other",
            password_hash=None,
        )
        session.add(other_user)
        await session.commit()
        other_user_id = other_user.id

    other_headers = {"Authorization": f"Bearer {create_access_token(other_user_id)}"}
    response = await client.get("/articles?q=kubernetes", headers=other_headers)
    assert response.status_code == 200
    assert response.json() == []


async def test_search_stems_english_articles_under_the_english_configuration(
    client: httpx.AsyncClient,
) -> None:
    """An article marked `en` is stored with english stemming; searching with the plural still
    reaches its singular stem, proving the per-article language config is actually used."""
    headers = await _headers(client)
    session_factory = async_sessionmaker(get_engine(), expire_on_commit=False)
    async with session_factory() as session:
        user = (await session.scalars(select(User))).one()
        feed = Feed(
            user_id=user.id,
            source_type=SourceType.MINIFLUX,
            external_feed_id="2",
            title="Feed",
            url="https://example.com/feed-en",
        )
        session.add(feed)
        await session.flush()
        session.add(
            Article(
                feed_id=feed.id,
                external_entry_id="en-1",
                title="Serverless databases are changing",
                url="https://example.com/en-1",
                content="A piece about running databases without managing servers",
                original_lang=Lang.EN,
                published_at=datetime(2026, 8, 13, tzinfo=UTC),
            )
        )
        await session.commit()

    response = await client.get("/articles?q=run", headers=headers)
    assert [article["title"] for article in response.json()] == [
        "Serverless databases are changing"
    ]
