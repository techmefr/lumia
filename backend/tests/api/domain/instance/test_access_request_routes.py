import httpx

VISITOR = {"email": "visiteur@example.com", "username": "visiteur"}


async def _open_to_requests(client: httpx.AsyncClient, headers: dict[str, str]) -> None:
    response = await client.patch(
        "/instance/settings", headers=headers, json={"access_mode": "on_approval"}
    )
    assert response.status_code == 200


async def test_a_closed_instance_refuses_an_access_request(
    client: httpx.AsyncClient, admin_headers: dict[str, str]
) -> None:
    response = await client.post("/access-requests", json=VISITOR)

    assert response.status_code == 403


async def test_a_visitor_asks_for_an_account_and_the_admin_sees_it_pending(
    client: httpx.AsyncClient, admin_headers: dict[str, str]
) -> None:
    await _open_to_requests(client, admin_headers)

    created = await client.post("/access-requests", json=VISITOR)
    assert created.status_code == 201
    assert created.json()["status"] == "pending"

    listed = await client.get("/access-requests", headers=admin_headers)
    assert [entry["email"] for entry in listed.json()] == [VISITOR["email"]]


async def test_an_address_already_known_cannot_ask_again(
    client: httpx.AsyncClient, admin_headers: dict[str, str]
) -> None:
    await _open_to_requests(client, admin_headers)
    assert (await client.post("/access-requests", json=VISITOR)).status_code == 201

    duplicate = await client.post("/access-requests", json=VISITOR)
    assert duplicate.status_code == 409

    as_the_admin = await client.post(
        "/access-requests", json={"email": "admin@example.com", "username": "admin"}
    )
    assert as_the_admin.status_code == 409


async def test_approving_a_request_creates_the_account_and_fills_the_instance(
    client: httpx.AsyncClient, admin_headers: dict[str, str]
) -> None:
    await _open_to_requests(client, admin_headers)
    await client.patch("/instance/settings", headers=admin_headers, json={"max_accounts": 2})
    created = await client.post("/access-requests", json=VISITOR)
    request_id = created.json()["id"]

    approved = await client.post(f"/access-requests/{request_id}/approve", headers=admin_headers)
    assert approved.status_code == 204

    accounts = await client.get("/instance/accounts", headers=admin_headers)
    assert sorted(entry["email"] for entry in accounts.json()) == [
        "admin@example.com",
        VISITOR["email"],
    ]

    settings = await client.get("/instance/settings", headers=admin_headers)
    assert settings.json()["account_count"] == 2


async def test_a_request_already_decided_cannot_be_decided_again(
    client: httpx.AsyncClient, admin_headers: dict[str, str]
) -> None:
    await _open_to_requests(client, admin_headers)
    created = await client.post("/access-requests", json=VISITOR)
    request_id = created.json()["id"]
    assert (
        await client.post(f"/access-requests/{request_id}/reject", headers=admin_headers)
    ).status_code == 204

    assert (
        await client.post(f"/access-requests/{request_id}/approve", headers=admin_headers)
    ).status_code == 409
    assert (
        await client.post(f"/access-requests/{request_id}/reject", headers=admin_headers)
    ).status_code == 409

    rejected = await client.get(
        "/access-requests", headers=admin_headers, params={"request_status": "rejected"}
    )
    assert [entry["email"] for entry in rejected.json()] == [VISITOR["email"]]
    assert rejected.json()[0]["decided_at"] is not None


async def test_a_full_instance_refuses_to_approve_a_request(
    client: httpx.AsyncClient, admin_headers: dict[str, str]
) -> None:
    await _open_to_requests(client, admin_headers)
    created = await client.post("/access-requests", json=VISITOR)
    request_id = created.json()["id"]
    assert (
        await client.patch("/instance/settings", headers=admin_headers, json={"max_accounts": 1})
    ).status_code == 200

    response = await client.post(f"/access-requests/{request_id}/approve", headers=admin_headers)

    assert response.status_code == 409
    accounts = await client.get("/instance/accounts", headers=admin_headers)
    assert len(accounts.json()) == 1


async def test_deciding_an_unknown_request_is_a_404(
    client: httpx.AsyncClient, admin_headers: dict[str, str]
) -> None:
    unknown = "00000000-0000-0000-0000-000000000000"

    assert (
        await client.post(f"/access-requests/{unknown}/approve", headers=admin_headers)
    ).status_code == 404
    assert (
        await client.post(f"/access-requests/{unknown}/reject", headers=admin_headers)
    ).status_code == 404


async def test_an_access_request_before_the_instance_exists_is_a_404(
    client: httpx.AsyncClient,
) -> None:
    response = await client.post("/access-requests", json=VISITOR)

    assert response.status_code == 404
