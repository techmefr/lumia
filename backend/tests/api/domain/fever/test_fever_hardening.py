import httpx
import pytest

from config.rate_limit import RateLimitConfig
from tests.api.domain.fever.conftest import admin_headers, issue_api_key, seed


@pytest.fixture
async def api_key(client: httpx.AsyncClient) -> str:
    return await issue_api_key(client, await admin_headers(client))


@pytest.mark.parametrize("value", ["\u00b2", "\u0663", "1,\u00b2,2", "\u0661\u0662"])
async def test_non_ascii_digits_are_ignored_instead_of_crashing(
    client: httpx.AsyncClient, api_key: str, value: str
) -> None:
    await seed()

    response = await client.post("/fever/?api&items", data={"api_key": api_key, "with_ids": value})

    assert response.status_code == 200
    assert response.json()["auth"] == 1


@pytest.mark.parametrize("value", ["\u00b2", "\u0663", "-\u00b2"])
async def test_a_non_ascii_digit_id_in_a_mark_is_ignored(
    client: httpx.AsyncClient, api_key: str, value: str
) -> None:
    await seed()

    response = await client.post(
        "/fever/?api", data={"api_key": api_key, "mark": "item", "as": "read", "id": value}
    )

    assert response.status_code == 200


async def test_the_endpoint_is_rate_limited_per_address(
    client: httpx.AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        "api.domain.fever.routes.get_rate_limit_config",
        lambda: RateLimitConfig(fever_max_attempts=2),
    )

    statuses = [(await client.get("/fever/?api")).status_code for _ in range(3)]

    assert statuses == [200, 200, 429]
