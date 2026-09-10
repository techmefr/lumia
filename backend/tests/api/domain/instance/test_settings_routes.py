import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from tests.api.domain.instance.conftest import add_member, headers_for


async def test_an_admin_reads_the_instance_settings(
    client: httpx.AsyncClient, admin_headers: dict[str, str]
) -> None:
    response = await client.get("/instance/settings", headers=admin_headers)

    assert response.status_code == 200
    body = response.json()
    assert body["max_accounts"] == 10
    assert body["disk_quota_mb"] == 1000
    assert body["access_mode"] == "closed"
    assert body["account_count"] == 1


async def test_an_admin_changes_the_quotas_and_they_are_reread(
    client: httpx.AsyncClient, admin_headers: dict[str, str]
) -> None:
    patch_response = await client.patch(
        "/instance/settings",
        headers=admin_headers,
        json={"max_accounts": 25, "disk_quota_mb": 2500, "access_mode": "on_approval"},
    )
    assert patch_response.status_code == 200

    get_response = await client.get("/instance/settings", headers=admin_headers)
    body = get_response.json()
    assert body["max_accounts"] == 25
    assert body["disk_quota_mb"] == 2500
    assert body["access_mode"] == "on_approval"


async def test_lowering_the_account_cap_under_the_existing_accounts_is_refused(
    client: httpx.AsyncClient, admin_headers: dict[str, str], session: AsyncSession
) -> None:
    await add_member(session)

    response = await client.patch(
        "/instance/settings", headers=admin_headers, json={"max_accounts": 1}
    )

    assert response.status_code == 409
    settings = await client.get("/instance/settings", headers=admin_headers)
    assert settings.json()["max_accounts"] == 10


async def test_a_member_sees_nothing_of_the_instance_settings(
    client: httpx.AsyncClient, admin_headers: dict[str, str], session: AsyncSession
) -> None:
    member = await add_member(session)
    member_headers = headers_for(member)

    assert (await client.get("/instance/settings", headers=member_headers)).status_code == 403
    assert (
        await client.patch("/instance/settings", headers=member_headers, json={"max_accounts": 99})
    ).status_code == 403
    assert (await client.get("/instance/accounts", headers=member_headers)).status_code == 403
    assert (await client.get("/access-requests", headers=member_headers)).status_code == 403


async def test_the_instance_settings_need_a_token_at_all(client: httpx.AsyncClient) -> None:
    assert (await client.get("/instance/settings")).status_code == 401
    assert (await client.get("/instance/accounts")).status_code == 401


async def test_the_access_mode_is_readable_without_an_account(
    client: httpx.AsyncClient, admin_headers: dict[str, str]
) -> None:
    response = await client.get("/instance/access-mode")

    assert response.status_code == 200
    assert response.json() == {"access_mode": "closed"}


async def test_the_access_mode_is_unknown_before_the_instance_exists(
    client: httpx.AsyncClient,
) -> None:
    response = await client.get("/instance/access-mode")

    assert response.status_code == 404


async def test_an_invalid_quota_is_refused_before_reaching_the_domain(
    client: httpx.AsyncClient, admin_headers: dict[str, str]
) -> None:
    response = await client.patch(
        "/instance/settings", headers=admin_headers, json={"disk_quota_mb": 0}
    )

    assert response.status_code == 422
