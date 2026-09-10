from collections.abc import AsyncIterator
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import httpx
import pytest

from api.main import app

ADMIN_PAYLOAD = {
    "email": "admin@example.com",
    "username": "admin",
    "password": "correct-horse-battery-staple",
    "max_accounts": 3,
}
INVITEE_PASSWORD = "another-correct-horse"


@pytest.fixture
async def client(db_schema: None) -> AsyncIterator[httpx.AsyncClient]:
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as async_client:
        yield async_client


async def _admin_headers(client: httpx.AsyncClient, **overrides: object) -> dict[str, str]:
    response = await client.post("/onboarding/admin", json={**ADMIN_PAYLOAD, **overrides})
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


async def _invite(
    client: httpx.AsyncClient,
    headers: dict[str, str],
    *,
    email: str = "invited@example.com",
    role: str = "member",
    raw_token: str = "the-raw-token",
) -> httpx.Response:
    with (
        patch("api.domain.user.invitation_service.send_email", new_callable=AsyncMock),
        patch(
            "api.domain.user.invitation_service.generate_opaque_token",
            return_value=raw_token,
        ),
    ):
        return await client.post(
            "/invitations", json={"email": email, "role": role}, headers=headers
        )


async def test_an_admin_can_invite_a_member(client: httpx.AsyncClient) -> None:
    headers = await _admin_headers(client)

    response = await _invite(client, headers)

    assert response.status_code == 201
    body = response.json()
    assert body["email"] == "invited@example.com"
    assert body["role"] == "member"


async def test_the_invitation_response_never_carries_the_token(client: httpx.AsyncClient) -> None:
    """The link belongs in the invitee's mailbox and nowhere else."""
    headers = await _admin_headers(client)

    response = await _invite(client, headers)

    assert "token" not in response.json()


async def test_the_invitee_gets_an_account_and_a_session(client: httpx.AsyncClient) -> None:
    headers = await _admin_headers(client)
    await _invite(client, headers)

    response = await client.post(
        "/invitations/accept",
        json={
            "token": "the-raw-token",
            "username": "reader",
            "password": INVITEE_PASSWORD,
        },
    )

    assert response.status_code == 201
    assert "access_token" in response.json()
    login = await client.post(
        "/auth/login", json={"email": "invited@example.com", "password": INVITEE_PASSWORD}
    )
    assert login.status_code == 200


async def test_the_new_member_is_not_an_admin(client: httpx.AsyncClient) -> None:
    headers = await _admin_headers(client)
    await _invite(client, headers)
    accepted = await client.post(
        "/invitations/accept",
        json={"token": "the-raw-token", "username": "reader", "password": INVITEE_PASSWORD},
    )
    member_headers = {"Authorization": f"Bearer {accepted.json()['access_token']}"}

    assert (await client.get("/me", headers=member_headers)).json()["role"] == "member"
    assert (await _invite(client, member_headers, email="friend@example.com")).status_code == 403


async def test_accepting_rejects_a_password_shorter_than_eight_characters(
    client: httpx.AsyncClient,
) -> None:
    headers = await _admin_headers(client)
    await _invite(client, headers)

    response = await client.post(
        "/invitations/accept",
        json={"token": "the-raw-token", "username": "reader", "password": "short1"},
    )

    assert response.status_code == 422


async def test_accepting_an_unknown_token_returns_401(client: httpx.AsyncClient) -> None:
    await _admin_headers(client)

    response = await client.post(
        "/invitations/accept",
        json={"token": "never-issued", "username": "reader", "password": INVITEE_PASSWORD},
    )

    assert response.status_code == 401


async def test_inviting_requires_being_logged_in(client: httpx.AsyncClient) -> None:
    await _admin_headers(client)

    response = await client.post("/invitations", json={"email": "invited@example.com"})

    assert response.status_code == 401


async def test_inviting_an_address_that_already_has_an_account_returns_409(
    client: httpx.AsyncClient,
) -> None:
    headers = await _admin_headers(client)

    response = await _invite(client, headers, email=str(ADMIN_PAYLOAD["email"]))

    assert response.status_code == 409


async def test_inviting_past_the_instance_ceiling_returns_409(client: httpx.AsyncClient) -> None:
    headers = await _admin_headers(client, max_accounts=1)

    response = await _invite(client, headers)

    assert response.status_code == 409
    assert response.json()["detail"] == "the instance has no seat left"


async def test_listing_shows_the_invitations_still_open(client: httpx.AsyncClient) -> None:
    headers = await _admin_headers(client)
    await _invite(client, headers)

    response = await client.get("/invitations", headers=headers)

    assert response.status_code == 200
    assert [invitation["email"] for invitation in response.json()] == ["invited@example.com"]


async def test_listing_requires_admin_rights(client: httpx.AsyncClient) -> None:
    headers = await _admin_headers(client)
    await _invite(client, headers)
    accepted = await client.post(
        "/invitations/accept",
        json={"token": "the-raw-token", "username": "reader", "password": INVITEE_PASSWORD},
    )
    member_headers = {"Authorization": f"Bearer {accepted.json()['access_token']}"}

    assert (await client.get("/invitations", headers=member_headers)).status_code == 403


async def test_an_admin_can_revoke_an_invitation_before_it_is_used(
    client: httpx.AsyncClient,
) -> None:
    headers = await _admin_headers(client)
    invitation_id = (await _invite(client, headers)).json()["id"]

    response = await client.delete(f"/invitations/{invitation_id}", headers=headers)

    assert response.status_code == 204
    accepted = await client.post(
        "/invitations/accept",
        json={"token": "the-raw-token", "username": "reader", "password": INVITEE_PASSWORD},
    )
    assert accepted.status_code == 401
    assert (await client.get("/invitations", headers=headers)).json() == []


async def test_revoking_an_unknown_invitation_returns_404(client: httpx.AsyncClient) -> None:
    headers = await _admin_headers(client)

    response = await client.delete(f"/invitations/{uuid4()}", headers=headers)

    assert response.status_code == 404
