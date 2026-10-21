from collections.abc import AsyncIterator
from datetime import UTC, datetime

import httpx
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker

from api.domain.article.models import Article
from api.domain.feed.models import Feed, SourceType
from api.domain.user.models import Role, User
from api.main import app
from api.technical.auth.hashing import hash_password
from api.technical.auth.jwt import create_access_token
from config.database import get_engine

ADMIN_PAYLOAD = {
    "email": "admin@example.com",
    "username": "admin",
    "password": "correct-horse-battery-staple",
}
UNKNOWN_ID = "00000000-0000-0000-0000-000000000000"
PASSAGE = {
    "quote": "le papier",
    "prefix": "Sur ",
    "suffix": " et",
    "start_offset": 4,
    "end_offset": 13,
}


@pytest.fixture
async def client(db_schema: None) -> AsyncIterator[httpx.AsyncClient]:
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as async_client:
        yield async_client


async def _headers(client: httpx.AsyncClient) -> dict[str, str]:
    response = await client.post("/onboarding/admin", json=ADMIN_PAYLOAD)
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


async def _seed_article() -> str:
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
        article = Article(
            feed_id=feed.id,
            external_entry_id="1",
            title="Le papier",
            url="https://example.com/1",
            content="<p>Sur le papier et l'encre.</p>",
            published_at=datetime(2026, 8, 12, tzinfo=UTC),
        )
        session.add(article)
        await session.commit()
        return str(article.id)


async def _other_reader_headers() -> dict[str, str]:
    session_factory = async_sessionmaker(get_engine(), expire_on_commit=False)
    async with session_factory() as session:
        admin = (await session.scalars(select(User))).one()
        other = User(
            instance_id=admin.instance_id,
            email="other@example.com",
            username="other",
            password_hash=hash_password("correct-horse-battery-staple"),
            role=Role.MEMBER,
        )
        session.add(other)
        await session.commit()
        return {"Authorization": f"Bearer {create_access_token(other.id)}"}


async def _create(
    client: httpx.AsyncClient,
    headers: dict[str, str],
    article_id: str,
    **overrides: object,
) -> httpx.Response:
    return await client.post(
        f"/articles/{article_id}/highlights", json={**PASSAGE, **overrides}, headers=headers
    )


async def test_a_reader_highlights_a_passage_and_finds_it_again(
    client: httpx.AsyncClient,
) -> None:
    headers = await _headers(client)
    article_id = await _seed_article()

    created = await _create(client, headers, article_id, note="A thought")

    assert created.status_code == 201
    body = created.json()
    assert body["quote"] == "le papier"
    assert body["note"] == "A thought"
    assert body["article_title"] == "Le papier"
    listed = await client.get(f"/articles/{article_id}/highlights", headers=headers)
    assert [item["id"] for item in listed.json()] == [body["id"]]
    assert listed.json()[0]["start_offset"] == 4


async def test_a_highlight_may_have_no_note(client: httpx.AsyncClient) -> None:
    headers = await _headers(client)
    article_id = await _seed_article()

    created = await _create(client, headers, article_id)

    assert created.json()["note"] is None


async def test_the_article_highlights_come_in_reading_order(client: httpx.AsyncClient) -> None:
    headers = await _headers(client)
    article_id = await _seed_article()
    await _create(client, headers, article_id, quote="later", start_offset=20, end_offset=25)
    await _create(client, headers, article_id, quote="sooner", start_offset=1, end_offset=7)

    listed = await client.get(f"/articles/{article_id}/highlights", headers=headers)

    assert [item["quote"] for item in listed.json()] == ["sooner", "later"]


async def test_the_global_list_spans_articles_newest_first(client: httpx.AsyncClient) -> None:
    headers = await _headers(client)
    article_id = await _seed_article()
    await _create(client, headers, article_id, quote="first")
    await _create(client, headers, article_id, quote="second")

    listed = await client.get("/highlights", headers=headers)

    assert [item["quote"] for item in listed.json()] == ["second", "first"]
    assert listed.json()[0]["article_id"] == article_id


async def test_the_note_can_be_edited_and_removed(client: httpx.AsyncClient) -> None:
    headers = await _headers(client)
    article_id = await _seed_article()
    highlight_id = (await _create(client, headers, article_id, note="old")).json()["id"]

    edited = await client.patch(
        f"/highlights/{highlight_id}", json={"note": "new"}, headers=headers
    )
    cleared = await client.patch(
        f"/highlights/{highlight_id}", json={"note": None}, headers=headers
    )

    assert edited.json()["note"] == "new"
    assert cleared.json()["note"] is None
    assert cleared.json()["quote"] == "le papier"


async def test_a_highlight_can_be_deleted(client: httpx.AsyncClient) -> None:
    headers = await _headers(client)
    article_id = await _seed_article()
    highlight_id = (await _create(client, headers, article_id)).json()["id"]

    deleted = await client.delete(f"/highlights/{highlight_id}", headers=headers)

    assert deleted.status_code == 204
    assert (await client.get("/highlights", headers=headers)).json() == []


@pytest.mark.parametrize(
    "overrides",
    [
        {"quote": ""},
        {"start_offset": -1},
        {"start_offset": 10, "end_offset": 10},
        {"start_offset": 10, "end_offset": 5},
        {"quote": "x" * 5001},
        {"note": "x" * 2001},
    ],
)
async def test_a_malformed_passage_is_refused(
    client: httpx.AsyncClient, overrides: dict[str, object]
) -> None:
    headers = await _headers(client)
    article_id = await _seed_article()

    response = await _create(client, headers, article_id, **overrides)

    assert response.status_code == 422


async def test_an_unknown_article_is_a_404(client: httpx.AsyncClient) -> None:
    headers = await _headers(client)

    assert (await _create(client, headers, UNKNOWN_ID)).status_code == 404
    assert (
        await client.get(f"/articles/{UNKNOWN_ID}/highlights", headers=headers)
    ).status_code == 404


async def test_an_unknown_highlight_is_a_404(client: httpx.AsyncClient) -> None:
    headers = await _headers(client)

    patched = await client.patch(f"/highlights/{UNKNOWN_ID}", json={"note": "x"}, headers=headers)
    deleted = await client.delete(f"/highlights/{UNKNOWN_ID}", headers=headers)

    assert patched.status_code == 404
    assert deleted.status_code == 404


async def test_another_readers_article_and_highlights_are_off_limits(
    client: httpx.AsyncClient,
) -> None:
    headers = await _headers(client)
    article_id = await _seed_article()
    highlight_id = (await _create(client, headers, article_id)).json()["id"]
    other = await _other_reader_headers()

    assert (await _create(client, other, article_id)).status_code == 404
    assert (
        await client.get(f"/articles/{article_id}/highlights", headers=other)
    ).status_code == 404
    assert (await client.get("/highlights", headers=other)).json() == []
    patched = await client.patch(
        f"/highlights/{highlight_id}", json={"note": "mine"}, headers=other
    )
    assert patched.status_code == 404
    assert (await client.delete(f"/highlights/{highlight_id}", headers=other)).status_code == 404
    assert len((await client.get("/highlights", headers=headers)).json()) == 1


async def test_every_route_requires_a_login(client: httpx.AsyncClient) -> None:
    await _headers(client)
    article_id = await _seed_article()

    assert (await client.get("/highlights")).status_code == 401
    assert (await client.get(f"/articles/{article_id}/highlights")).status_code == 401
    assert (
        await client.post(f"/articles/{article_id}/highlights", json=PASSAGE)
    ).status_code == 401
    assert (await client.patch(f"/highlights/{UNKNOWN_ID}", json={"note": None})).status_code == 401
    assert (await client.delete(f"/highlights/{UNKNOWN_ID}")).status_code == 401
