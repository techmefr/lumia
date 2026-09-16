from collections.abc import AsyncIterator
from datetime import UTC, datetime
from typing import Any

import httpx
import pytest
from sqlalchemy import select
from sqlalchemy.exc import OperationalError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from api.domain.article.models import Article
from api.domain.feed.models import Feed, SourceType
from api.domain.playlist.models import PlaylistItem
from api.domain.user.models import User
from api.main import app
from config.database import get_engine

ADMIN_PAYLOAD = {
    "email": "admin@example.com",
    "username": "admin",
    "password": "correct-horse-battery-staple",
}
UNKNOWN_ID = "00000000-0000-0000-0000-000000000000"


@pytest.fixture
async def client(db_schema: None) -> AsyncIterator[httpx.AsyncClient]:
    transport = httpx.ASGITransport(app=app, raise_app_exceptions=False)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as async_client:
        yield async_client


async def _headers(client: httpx.AsyncClient) -> dict[str, str]:
    response = await client.post("/onboarding/admin", json=ADMIN_PAYLOAD)
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


async def _seed_articles(count: int = 3) -> list[str]:
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
        articles = [
            Article(
                feed_id=feed.id,
                external_entry_id=str(index),
                title=f"Article {index}",
                url=f"https://example.com/{index}",
                content=" ".join(["mot"] * 400),
                published_at=datetime(2026, 8, 12, tzinfo=UTC),
            )
            for index in range(count)
        ]
        session.add_all(articles)
        await session.commit()
        return [str(article.id) for article in articles]


async def _create_playlist(client: httpx.AsyncClient, headers: dict[str, str]) -> str:
    response = await client.post("/playlists", json={"name": "Trajet"}, headers=headers)
    return str(response.json()["id"])


async def _item_count() -> int:
    session_factory = async_sessionmaker(get_engine(), expire_on_commit=False)
    async with session_factory() as session:
        return len(list(await session.scalars(select(PlaylistItem))))


async def test_a_selection_is_added_in_the_order_it_was_given(client: httpx.AsyncClient) -> None:
    headers = await _headers(client)
    articles = await _seed_articles()
    playlist_id = await _create_playlist(client, headers)

    response = await client.post(
        f"/playlists/{playlist_id}/items/bulk",
        json={"article_ids": articles},
        headers=headers,
    )

    assert response.status_code == 200
    assert response.json()["moved"] == 3
    detail = (await client.get(f"/playlists/{playlist_id}", headers=headers)).json()
    assert [article["title"] for article in detail["articles"]] == [
        "Article 0",
        "Article 1",
        "Article 2",
    ]


async def test_articles_already_in_the_playlist_are_left_out_of_the_report(
    client: httpx.AsyncClient,
) -> None:
    """An undo removes the reported ids, so it must not remove what was in the playlist before."""
    headers = await _headers(client)
    articles = await _seed_articles()
    playlist_id = await _create_playlist(client, headers)
    await client.post(
        f"/playlists/{playlist_id}/items",
        json={"article_id": articles[0]},
        headers=headers,
    )

    response = await client.post(
        f"/playlists/{playlist_id}/items/bulk", json={"article_ids": articles}, headers=headers
    )

    assert response.json() == {"moved": 2, "article_ids": articles[1:]}


async def test_present_false_takes_the_selection_back_out(client: httpx.AsyncClient) -> None:
    headers = await _headers(client)
    articles = await _seed_articles()
    playlist_id = await _create_playlist(client, headers)
    added = (
        await client.post(
            f"/playlists/{playlist_id}/items/bulk", json={"article_ids": articles}, headers=headers
        )
    ).json()["article_ids"]

    response = await client.post(
        f"/playlists/{playlist_id}/items/bulk",
        json={"article_ids": added, "present": False},
        headers=headers,
    )

    assert response.json()["moved"] == 3
    detail = (await client.get(f"/playlists/{playlist_id}", headers=headers)).json()
    assert detail["articles"] == []


async def test_the_remaining_items_keep_a_dense_order_after_a_bulk_removal(
    client: httpx.AsyncClient,
) -> None:
    headers = await _headers(client)
    articles = await _seed_articles()
    playlist_id = await _create_playlist(client, headers)
    await client.post(
        f"/playlists/{playlist_id}/items/bulk", json={"article_ids": articles}, headers=headers
    )

    await client.post(
        f"/playlists/{playlist_id}/items/bulk",
        json={"article_ids": [articles[0]], "present": False},
        headers=headers,
    )

    session_factory = async_sessionmaker(get_engine(), expire_on_commit=False)
    async with session_factory() as session:
        positions = sorted(item.position for item in await session.scalars(select(PlaylistItem)))
    assert positions == [0, 1]


@pytest.mark.parametrize(
    "body",
    [
        pytest.param({}, id="no scope at all"),
        pytest.param({"all": False}, id="all passed but false"),
        pytest.param({"article_ids": [], "all": True}, id="a list and all"),
    ],
)
async def test_anything_but_exactly_one_scope_is_rejected(
    client: httpx.AsyncClient, body: dict[str, Any]
) -> None:
    """The same contract as mark-read: a bulk add cannot reach the library by omission."""
    headers = await _headers(client)
    playlist_id = await _create_playlist(client, headers)

    response = await client.post(f"/playlists/{playlist_id}/items/bulk", json=body, headers=headers)

    assert response.status_code == 422


async def test_an_unknown_playlist_is_not_found(client: httpx.AsyncClient) -> None:
    headers = await _headers(client)
    articles = await _seed_articles()

    response = await client.post(
        f"/playlists/{UNKNOWN_ID}/items/bulk", json={"article_ids": articles}, headers=headers
    )

    assert response.status_code == 404


async def test_a_write_failing_halfway_adds_nothing_at_all(
    client: httpx.AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    headers = await _headers(client)
    articles = await _seed_articles()
    playlist_id = await _create_playlist(client, headers)

    async def fail(_self: AsyncSession) -> None:
        raise OperationalError("bulk", None, Exception("connection lost"))

    monkeypatch.setattr(AsyncSession, "commit", fail)

    response = await client.post(
        f"/playlists/{playlist_id}/items/bulk", json={"article_ids": articles}, headers=headers
    )

    assert response.status_code == 500
    monkeypatch.undo()
    assert await _item_count() == 0
