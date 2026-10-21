import httpx
from sqlalchemy import select

from api.domain.fever.key_service import derive_api_key
from api.domain.fever.models import FeverKey
from api.domain.user.account_service import delete_account
from api.domain.user.models import User
from tests.api.domain.fever.conftest import (
    ADMIN_PAYLOAD,
    add_second_reader,
    admin_headers,
    sessions,
)


async def _auth(client: httpx.AsyncClient, api_key: str) -> int:
    response = await client.post("/fever/?api", data={"api_key": api_key})
    return int(response.json()["auth"])


async def test_a_reader_without_a_key_sees_it_disabled(client: httpx.AsyncClient) -> None:
    response = await client.get("/me/fever", headers=await admin_headers(client))

    assert response.json() == {"enabled": False, "created_at": None}


async def test_the_key_endpoints_need_a_signed_in_reader(client: httpx.AsyncClient) -> None:
    assert (await client.get("/me/fever")).status_code in (401, 403)
    assert (await client.post("/me/fever")).status_code in (401, 403)
    assert (await client.delete("/me/fever")).status_code in (401, 403)


async def test_creating_a_key_returns_the_login_to_type_into_the_app(
    client: httpx.AsyncClient,
) -> None:
    headers = await admin_headers(client)

    response = await client.post("/me/fever", headers=headers)

    assert response.status_code == 201
    body = response.json()
    assert body["email"] == ADMIN_PAYLOAD["email"]
    assert len(body["secret"]) >= 32
    assert body["secret"] != ADMIN_PAYLOAD["password"]
    assert await _auth(client, derive_api_key(body["email"], body["secret"])) == 1
    status = (await client.get("/me/fever", headers=headers)).json()
    assert status["enabled"] is True
    assert status["created_at"] is not None


async def test_the_database_holds_neither_the_secret_nor_the_api_key(
    client: httpx.AsyncClient,
) -> None:
    created = (await client.post("/me/fever", headers=await admin_headers(client))).json()

    async with sessions()() as session:
        stored = (await session.scalars(select(FeverKey))).one()

    api_key = derive_api_key(created["email"], created["secret"])
    assert stored.key_hash not in (created["secret"], api_key)
    assert len(stored.key_hash) == 64


async def test_asking_again_replaces_the_key(client: httpx.AsyncClient) -> None:
    headers = await admin_headers(client)
    first = (await client.post("/me/fever", headers=headers)).json()
    second = (await client.post("/me/fever", headers=headers)).json()

    assert first["secret"] != second["secret"]
    assert await _auth(client, derive_api_key(first["email"], first["secret"])) == 0
    assert await _auth(client, derive_api_key(second["email"], second["secret"])) == 1
    async with sessions()() as session:
        assert len((await session.scalars(select(FeverKey))).all()) == 1


async def test_revoking_stops_the_key_working(client: httpx.AsyncClient) -> None:
    headers = await admin_headers(client)
    created = (await client.post("/me/fever", headers=headers)).json()

    response = await client.delete("/me/fever", headers=headers)

    assert response.status_code == 204
    assert await _auth(client, derive_api_key(created["email"], created["secret"])) == 0
    assert (await client.get("/me/fever", headers=headers)).json()["enabled"] is False


async def test_revoking_without_a_key_is_a_404(client: httpx.AsyncClient) -> None:
    response = await client.delete("/me/fever", headers=await admin_headers(client))

    assert response.status_code == 404


async def test_a_reader_cannot_revoke_anothers_key(client: httpx.AsyncClient) -> None:
    admin = await admin_headers(client)
    created = (await client.post("/me/fever", headers=admin)).json()
    other = await add_second_reader()

    response = await client.delete("/me/fever", headers=other)

    assert response.status_code == 404
    assert await _auth(client, derive_api_key(created["email"], created["secret"])) == 1


async def test_deleting_the_account_deletes_its_key(client: httpx.AsyncClient) -> None:
    await admin_headers(client)
    other = await add_second_reader()
    created = (await client.post("/me/fever", headers=other)).json()

    async with sessions()() as session:
        second = (await session.scalars(select(User).where(User.email == created["email"]))).one()
        await delete_account(session, second.id)

    assert await _auth(client, derive_api_key(created["email"], created["secret"])) == 0
    async with sessions()() as session:
        assert (await session.scalars(select(FeverKey))).all() == []
