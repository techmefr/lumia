import httpx
import pytest

from api.domain.instance import access_request_service
from config.rate_limit import get_rate_limit_config


def _visitor(index: int) -> dict[str, str]:
    return {"email": f"Visiteur{index}@Example.com", "username": f"visiteur{index}"}


async def _open_to_requests(client: httpx.AsyncClient, headers: dict[str, str]) -> None:
    response = await client.patch(
        "/instance/settings", headers=headers, json={"access_mode": "on_approval"}
    )
    assert response.status_code == 200


async def test_requests_from_one_address_are_rate_limited(
    client: httpx.AsyncClient, admin_headers: dict[str, str]
) -> None:
    await _open_to_requests(client, admin_headers)
    allowance = get_rate_limit_config().access_request_max_attempts

    statuses = [
        (await client.post("/access-requests", json=_visitor(index))).status_code
        for index in range(allowance + 1)
    ]

    assert statuses[:allowance] == [201] * allowance
    assert statuses[-1] == 429


async def test_the_pending_queue_is_bounded(
    client: httpx.AsyncClient, admin_headers: dict[str, str], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(access_request_service, "MAX_PENDING_ACCESS_REQUESTS", 2)
    await _open_to_requests(client, admin_headers)

    statuses = [
        (await client.post("/access-requests", json=_visitor(index))).status_code
        for index in range(3)
    ]

    assert statuses == [201, 201, 429]


async def test_the_address_is_stored_in_lowercase(
    client: httpx.AsyncClient, admin_headers: dict[str, str]
) -> None:
    await _open_to_requests(client, admin_headers)

    await client.post("/access-requests", json=_visitor(1))

    listed = await client.get("/access-requests", headers=admin_headers)
    assert [entry["email"] for entry in listed.json()] == ["visiteur1@example.com"]


async def test_the_same_address_in_another_case_is_a_duplicate(
    client: httpx.AsyncClient, admin_headers: dict[str, str]
) -> None:
    await _open_to_requests(client, admin_headers)
    await client.post("/access-requests", json=_visitor(1))

    duplicate = await client.post(
        "/access-requests", json={"email": "VISITEUR1@EXAMPLE.COM", "username": "again"}
    )

    assert duplicate.status_code == 409


async def test_the_list_is_paginated(
    client: httpx.AsyncClient, admin_headers: dict[str, str]
) -> None:
    await _open_to_requests(client, admin_headers)
    for index in range(3):
        await client.post("/access-requests", json=_visitor(index))

    first_page = await client.get("/access-requests", headers=admin_headers, params={"limit": 2})
    second_page = await client.get(
        "/access-requests", headers=admin_headers, params={"limit": 2, "offset": 2}
    )

    assert len(first_page.json()) == 2
    assert len(second_page.json()) == 1
    assert {entry["id"] for entry in first_page.json()}.isdisjoint(
        {entry["id"] for entry in second_page.json()}
    )


async def test_the_page_size_is_capped(
    client: httpx.AsyncClient, admin_headers: dict[str, str]
) -> None:
    response = await client.get("/access-requests", headers=admin_headers, params={"limit": 201})

    assert response.status_code == 422
