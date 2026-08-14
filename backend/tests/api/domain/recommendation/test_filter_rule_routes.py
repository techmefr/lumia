from collections.abc import AsyncIterator
from uuid import UUID

import httpx
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker

from api.domain.recommendation.filter_rule_service import delete_rule, list_rules
from api.domain.user.models import User
from api.main import app
from config.database import get_engine

ADMIN_PAYLOAD = {
    "email": "admin@example.com",
    "username": "admin",
    "password": "correct-horse-battery-staple",
}
OTHER_EMAIL = "other@example.com"


@pytest.fixture
async def client(db_schema: None) -> AsyncIterator[httpx.AsyncClient]:
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as async_client:
        yield async_client


async def _headers(client: httpx.AsyncClient) -> dict[str, str]:
    response = await client.post("/onboarding/admin", json=ADMIN_PAYLOAD)
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


async def test_create_then_list_returns_the_rule(client: httpx.AsyncClient) -> None:
    headers = await _headers(client)

    created = await client.post(
        "/filter-rules", json={"term": "Bitcoin", "mode": "mute"}, headers=headers
    )
    assert created.status_code == 201
    # The term is normalised on the way in, so the same word typed differently is one rule.
    assert created.json()["term"] == "bitcoin"

    listed = await client.get("/filter-rules", headers=headers)
    assert listed.status_code == 200
    assert [(rule["term"], rule["mode"]) for rule in listed.json()] == [("bitcoin", "mute")]


async def test_creating_the_same_term_twice_returns_the_same_rule(
    client: httpx.AsyncClient,
) -> None:
    headers = await _headers(client)
    payload = {"term": "bitcoin", "mode": "boost"}

    first = await client.post("/filter-rules", json=payload, headers=headers)
    second = await client.post("/filter-rules", json=payload, headers=headers)

    assert first.json()["id"] == second.json()["id"]
    listed = await client.get("/filter-rules", headers=headers)
    assert len(listed.json()) == 1


async def test_the_same_term_can_exist_in_both_modes(client: httpx.AsyncClient) -> None:
    headers = await _headers(client)

    await client.post("/filter-rules", json={"term": "ia", "mode": "boost"}, headers=headers)
    await client.post("/filter-rules", json={"term": "ia", "mode": "mute"}, headers=headers)

    listed = await client.get("/filter-rules", headers=headers)
    assert sorted(rule["mode"] for rule in listed.json()) == ["boost", "mute"]


async def test_delete_removes_the_rule(client: httpx.AsyncClient) -> None:
    headers = await _headers(client)
    created = await client.post(
        "/filter-rules", json={"term": "football", "mode": "mute"}, headers=headers
    )

    deleted = await client.delete(f"/filter-rules/{created.json()['id']}", headers=headers)

    assert deleted.status_code == 204
    assert (await client.get("/filter-rules", headers=headers)).json() == []


async def test_deleting_an_unknown_rule_returns_404(client: httpx.AsyncClient) -> None:
    headers = await _headers(client)

    response = await client.delete(
        "/filter-rules/00000000-0000-0000-0000-000000000000", headers=headers
    )

    assert response.status_code == 404


async def test_a_rule_belongs_to_its_owner_only(client: httpx.AsyncClient) -> None:
    headers = await _headers(client)
    created = await client.post(
        "/filter-rules", json={"term": "bitcoin", "mode": "mute"}, headers=headers
    )
    rule_id = UUID(created.json()["id"])

    session_factory = async_sessionmaker(get_engine(), expire_on_commit=False)
    async with session_factory() as session:
        owner = (await session.scalars(select(User))).one()
        other = User(
            instance_id=owner.instance_id,
            email=OTHER_EMAIL,
            username="other",
            password_hash=None,
        )
        session.add(other)
        await session.commit()

        assert await list_rules(session, other.id) == []
        assert await delete_rule(session, other.id, rule_id) is False
        assert len(await list_rules(session, owner.id)) == 1


async def test_filter_rules_without_a_token_returns_401(client: httpx.AsyncClient) -> None:
    assert (await client.get("/filter-rules")).status_code == 401


async def test_an_unknown_mode_is_rejected(client: httpx.AsyncClient) -> None:
    headers = await _headers(client)

    response = await client.post(
        "/filter-rules", json={"term": "bitcoin", "mode": "ignore"}, headers=headers
    )

    assert response.status_code == 422
