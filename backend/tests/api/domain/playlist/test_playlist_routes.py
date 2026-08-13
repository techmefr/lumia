from collections.abc import AsyncIterator
from datetime import UTC, datetime

import httpx
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker

from api.domain.article.models import Article
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
UNKNOWN_ID = "00000000-0000-0000-0000-000000000000"


@pytest.fixture
async def client(db_schema: None) -> AsyncIterator[httpx.AsyncClient]:
    transport = httpx.ASGITransport(app=app)
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
    assert response.status_code == 201
    return str(response.json()["id"])


async def test_create_and_list_playlists(client: httpx.AsyncClient) -> None:
    headers = await _headers(client)
    await _create_playlist(client, headers)

    listed = (await client.get("/playlists", headers=headers)).json()
    assert [playlist["name"] for playlist in listed] == ["Trajet"]
    assert listed[0]["item_count"] == 0
    assert listed[0]["total_reading_minutes"] == 0


async def test_add_articles_keeps_insertion_order(client: httpx.AsyncClient) -> None:
    headers = await _headers(client)
    article_ids = await _seed_articles()
    playlist_id = await _create_playlist(client, headers)

    for article_id in article_ids:
        response = await client.post(
            f"/playlists/{playlist_id}/items", json={"article_id": article_id}, headers=headers
        )
        assert response.status_code == 200

    detail = (await client.get(f"/playlists/{playlist_id}", headers=headers)).json()
    assert [article["title"] for article in detail["articles"]] == [
        "Article 0",
        "Article 1",
        "Article 2",
    ]


async def test_adding_the_same_article_twice_is_a_no_op(client: httpx.AsyncClient) -> None:
    headers = await _headers(client)
    article_ids = await _seed_articles(1)
    playlist_id = await _create_playlist(client, headers)

    await client.post(
        f"/playlists/{playlist_id}/items", json={"article_id": article_ids[0]}, headers=headers
    )
    response = await client.post(
        f"/playlists/{playlist_id}/items", json={"article_id": article_ids[0]}, headers=headers
    )
    assert len(response.json()["articles"]) == 1


async def test_playlist_summary_totals_the_reading_time(client: httpx.AsyncClient) -> None:
    headers = await _headers(client)
    article_ids = await _seed_articles(2)
    playlist_id = await _create_playlist(client, headers)
    for article_id in article_ids:
        await client.post(
            f"/playlists/{playlist_id}/items", json={"article_id": article_id}, headers=headers
        )

    listed = (await client.get("/playlists", headers=headers)).json()
    # 400 words each at 200 words/minute.
    assert listed[0] == {
        "id": playlist_id,
        "name": "Trajet",
        "item_count": 2,
        "total_reading_minutes": 4,
    }


async def test_remove_article_renumbers_the_rest(client: httpx.AsyncClient) -> None:
    headers = await _headers(client)
    article_ids = await _seed_articles()
    playlist_id = await _create_playlist(client, headers)
    for article_id in article_ids:
        await client.post(
            f"/playlists/{playlist_id}/items", json={"article_id": article_id}, headers=headers
        )

    response = await client.delete(
        f"/playlists/{playlist_id}/items/{article_ids[0]}", headers=headers
    )
    assert [article["title"] for article in response.json()["articles"]] == [
        "Article 1",
        "Article 2",
    ]


async def test_removing_an_absent_article_returns_404(client: httpx.AsyncClient) -> None:
    headers = await _headers(client)
    article_ids = await _seed_articles(1)
    playlist_id = await _create_playlist(client, headers)

    response = await client.delete(
        f"/playlists/{playlist_id}/items/{article_ids[0]}", headers=headers
    )
    assert response.status_code == 404


async def test_reorder_applies_the_given_order(client: httpx.AsyncClient) -> None:
    headers = await _headers(client)
    article_ids = await _seed_articles()
    playlist_id = await _create_playlist(client, headers)
    for article_id in article_ids:
        await client.post(
            f"/playlists/{playlist_id}/items", json={"article_id": article_id}, headers=headers
        )

    response = await client.put(
        f"/playlists/{playlist_id}/order",
        json={"article_ids": [article_ids[2], article_ids[0], article_ids[1]]},
        headers=headers,
    )
    assert [article["title"] for article in response.json()["articles"]] == [
        "Article 2",
        "Article 0",
        "Article 1",
    ]


async def test_reorder_keeps_ids_missing_from_the_payload(client: httpx.AsyncClient) -> None:
    headers = await _headers(client)
    article_ids = await _seed_articles()
    playlist_id = await _create_playlist(client, headers)
    for article_id in article_ids:
        await client.post(
            f"/playlists/{playlist_id}/items", json={"article_id": article_id}, headers=headers
        )

    response = await client.put(
        f"/playlists/{playlist_id}/order",
        json={"article_ids": [article_ids[2]]},
        headers=headers,
    )
    titles = [article["title"] for article in response.json()["articles"]]
    assert titles[0] == "Article 2"
    assert sorted(titles[1:]) == ["Article 0", "Article 1"]


async def test_rename_playlist(client: httpx.AsyncClient) -> None:
    headers = await _headers(client)
    playlist_id = await _create_playlist(client, headers)

    response = await client.patch(
        f"/playlists/{playlist_id}", json={"name": "Matin"}, headers=headers
    )
    assert response.json()["name"] == "Matin"


async def test_delete_playlist_keeps_its_articles(client: httpx.AsyncClient) -> None:
    headers = await _headers(client)
    article_ids = await _seed_articles(1)
    playlist_id = await _create_playlist(client, headers)
    await client.post(
        f"/playlists/{playlist_id}/items", json={"article_id": article_ids[0]}, headers=headers
    )

    assert (await client.delete(f"/playlists/{playlist_id}", headers=headers)).status_code == 204
    assert (await client.get("/playlists", headers=headers)).json() == []
    assert len((await client.get("/articles", headers=headers)).json()) == 1


async def test_adding_an_article_of_another_user_returns_404(client: httpx.AsyncClient) -> None:
    await _headers(client)
    article_ids = await _seed_articles(1)

    session_factory = async_sessionmaker(get_engine(), expire_on_commit=False)
    async with session_factory() as session:
        user = (await session.scalars(select(User))).one()
        other = User(
            instance_id=user.instance_id,
            email="other@example.com",
            username="other",
            password_hash=None,
        )
        session.add(other)
        await session.commit()
        other_headers = {"Authorization": f"Bearer {create_access_token(other.id)}"}

    other_playlist_id = (
        await client.post("/playlists", json={"name": "Autre"}, headers=other_headers)
    ).json()["id"]

    response = await client.post(
        f"/playlists/{other_playlist_id}/items",
        json={"article_id": article_ids[0]},
        headers=other_headers,
    )
    assert response.status_code == 404


async def test_another_users_playlist_is_not_reachable(client: httpx.AsyncClient) -> None:
    headers = await _headers(client)
    playlist_id = await _create_playlist(client, headers)

    session_factory = async_sessionmaker(get_engine(), expire_on_commit=False)
    async with session_factory() as session:
        user = (await session.scalars(select(User))).one()
        other = User(
            instance_id=user.instance_id,
            email="other@example.com",
            username="other",
            password_hash=None,
        )
        session.add(other)
        await session.commit()
        other_headers = {"Authorization": f"Bearer {create_access_token(other.id)}"}

    assert (
        await client.get(f"/playlists/{playlist_id}", headers=other_headers)
    ).status_code == 404
    assert (
        await client.patch(f"/playlists/{playlist_id}", json={"name": "X"}, headers=other_headers)
    ).status_code == 404
    assert (
        await client.delete(f"/playlists/{playlist_id}", headers=other_headers)
    ).status_code == 404


async def test_unknown_playlist_returns_404(client: httpx.AsyncClient) -> None:
    headers = await _headers(client)
    assert (await client.get(f"/playlists/{UNKNOWN_ID}", headers=headers)).status_code == 404
