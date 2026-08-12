from collections.abc import AsyncIterator

import httpx
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker

from api.domain.user.models import Instance, User
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


async def test_list_folders_is_empty_by_default(client: httpx.AsyncClient) -> None:
    headers = await _headers(client)
    response = await client.get("/folders", headers=headers)
    assert response.status_code == 200
    assert response.json() == []


async def test_create_folder_attaches_it_to_the_current_user(client: httpx.AsyncClient) -> None:
    headers = await _headers(client)

    create_response = await client.post("/folders", headers=headers, json={"name": "Tech"})
    assert create_response.status_code == 201
    assert create_response.json()["name"] == "Tech"

    list_response = await client.get("/folders", headers=headers)
    names = [folder["name"] for folder in list_response.json()]
    assert names == ["Tech"]


async def test_folders_are_not_shared_between_users(client: httpx.AsyncClient) -> None:
    headers = await _headers(client)
    await client.post("/folders", headers=headers, json={"name": "Tech"})

    session_factory = async_sessionmaker(get_engine(), expire_on_commit=False)
    async with session_factory() as session:
        instance = (await session.scalars(select(Instance))).one()
        other_user = User(
            instance_id=instance.id,
            email="member@example.com",
            username="member",
            password_hash=None,
        )
        session.add(other_user)
        await session.commit()
        other_user_id = other_user.id

    other_headers = {"Authorization": f"Bearer {create_access_token(other_user_id)}"}
    list_response = await client.get("/folders", headers=other_headers)
    assert list_response.json() == []


async def test_list_folders_without_a_token_returns_401(client: httpx.AsyncClient) -> None:
    response = await client.get("/folders")
    assert response.status_code == 401
