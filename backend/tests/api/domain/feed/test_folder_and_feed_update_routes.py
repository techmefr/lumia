from collections.abc import AsyncIterator

import httpx
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker

from api.domain.feed.models import Feed, Folder, SourceType
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


async def _seed() -> dict[str, str]:
    session_factory = async_sessionmaker(get_engine(), expire_on_commit=False)
    async with session_factory() as session:
        user = (await session.scalars(select(User))).one()
        folder = Folder(user_id=user.id, name="Tech")
        other_folder = Folder(user_id=user.id, name="Perso")
        session.add_all([folder, other_folder])
        await session.flush()
        feed = Feed(
            user_id=user.id,
            folder_id=folder.id,
            source_type=SourceType.MINIFLUX,
            external_feed_id="1",
            title="Korben",
            url="https://example.com/1",
        )
        session.add(feed)
        await session.commit()
        return {
            "folder_id": str(folder.id),
            "other_folder_id": str(other_folder.id),
            "feed_id": str(feed.id),
        }


async def test_rename_folder(client: httpx.AsyncClient) -> None:
    headers = await _headers(client)
    ids = await _seed()

    response = await client.patch(
        f"/folders/{ids['folder_id']}", json={"name": "Veille"}, headers=headers
    )
    assert response.status_code == 200
    assert response.json()["name"] == "Veille"

    listed = (await client.get("/folders", headers=headers)).json()
    assert sorted(folder["name"] for folder in listed) == ["Perso", "Veille"]


async def test_rename_an_unknown_folder_returns_404(client: httpx.AsyncClient) -> None:
    headers = await _headers(client)
    response = await client.patch(f"/folders/{UNKNOWN_ID}", json={"name": "X"}, headers=headers)
    assert response.status_code == 404


async def test_rename_another_users_folder_returns_404(client: httpx.AsyncClient) -> None:
    await _headers(client)
    ids = await _seed()

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

    response = await client.patch(
        f"/folders/{ids['folder_id']}", json={"name": "Vole"}, headers=other_headers
    )
    assert response.status_code == 404


async def test_delete_folder_unfiles_its_feeds_instead_of_deleting_them(
    client: httpx.AsyncClient,
) -> None:
    headers = await _headers(client)
    ids = await _seed()

    response = await client.delete(f"/folders/{ids['folder_id']}", headers=headers)
    assert response.status_code == 204

    feeds = (await client.get("/feeds", headers=headers)).json()
    assert [feed["folder_id"] for feed in feeds] == [None]
    folders = (await client.get("/folders", headers=headers)).json()
    assert [folder["name"] for folder in folders] == ["Perso"]


async def test_delete_an_unknown_folder_returns_404(client: httpx.AsyncClient) -> None:
    headers = await _headers(client)
    response = await client.delete(f"/folders/{UNKNOWN_ID}", headers=headers)
    assert response.status_code == 404


async def test_retitle_feed(client: httpx.AsyncClient) -> None:
    headers = await _headers(client)
    ids = await _seed()

    response = await client.patch(
        f"/feeds/{ids['feed_id']}", json={"title": "Korben.info"}, headers=headers
    )
    assert response.status_code == 200
    assert response.json()["title"] == "Korben.info"
    assert response.json()["folder_id"] == ids["folder_id"]


async def test_move_feed_to_another_folder(client: httpx.AsyncClient) -> None:
    headers = await _headers(client)
    ids = await _seed()

    response = await client.patch(
        f"/feeds/{ids['feed_id']}", json={"folder_id": ids["other_folder_id"]}, headers=headers
    )
    assert response.json()["folder_id"] == ids["other_folder_id"]
    assert response.json()["title"] == "Korben"


async def test_unfile_feed_with_an_explicit_null(client: httpx.AsyncClient) -> None:
    headers = await _headers(client)
    ids = await _seed()

    response = await client.patch(
        f"/feeds/{ids['feed_id']}", json={"folder_id": None}, headers=headers
    )
    assert response.json()["folder_id"] is None


async def test_omitting_folder_id_leaves_the_feed_where_it_is(client: httpx.AsyncClient) -> None:
    headers = await _headers(client)
    ids = await _seed()

    response = await client.patch(
        f"/feeds/{ids['feed_id']}", json={"title": "Autre"}, headers=headers
    )
    assert response.json()["folder_id"] == ids["folder_id"]


async def test_move_feed_to_an_unknown_folder_returns_404(client: httpx.AsyncClient) -> None:
    headers = await _headers(client)
    ids = await _seed()

    response = await client.patch(
        f"/feeds/{ids['feed_id']}", json={"folder_id": UNKNOWN_ID}, headers=headers
    )
    assert response.status_code == 404


async def test_patch_an_unknown_feed_returns_404(client: httpx.AsyncClient) -> None:
    headers = await _headers(client)
    response = await client.patch(f"/feeds/{UNKNOWN_ID}", json={"title": "X"}, headers=headers)
    assert response.status_code == 404
