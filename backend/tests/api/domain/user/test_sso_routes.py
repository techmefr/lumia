from collections.abc import AsyncIterator

import httpx
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker

from api.domain.user.models import Instance, User
from api.main import app
from api.technical.auth.oidc_client import get_oidc_transport
from api.technical.crypto.secret_box import encrypt_secret
from config.database import get_engine

ADMIN_PAYLOAD = {
    "email": "admin@example.com",
    "username": "admin",
    "password": "correct-horse-battery-staple",
}

DISCOVERY_PAYLOAD = {
    "authorization_endpoint": "https://idp.example.com/authorize",
    "token_endpoint": "https://idp.example.com/token",
    "userinfo_endpoint": "https://idp.example.com/userinfo",
}


@pytest.fixture
async def client(db_schema: None) -> AsyncIterator[httpx.AsyncClient]:
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(
        transport=transport, base_url="http://test", follow_redirects=False
    ) as async_client:
        yield async_client
    app.dependency_overrides.pop(get_oidc_transport, None)


async def _onboard(client: httpx.AsyncClient) -> None:
    response = await client.post("/onboarding/admin", json=ADMIN_PAYLOAD)
    assert response.status_code == 201


async def _configure_sso(client_secret: str = "the-client-secret") -> None:
    session_factory = async_sessionmaker(get_engine(), expire_on_commit=False)
    async with session_factory() as session:
        instance = (await session.scalars(select(Instance))).one()
        instance.oidc_issuer = "https://idp.example.com"
        instance.oidc_client_id = "lumia"
        instance.oidc_client_secret_encrypted = encrypt_secret(client_secret)
        instance.oidc_redirect_uri = "https://lumia.example.com/auth/sso/callback"
        await session.commit()


def _mock_transport(*, sub: str, email: str) -> httpx.MockTransport:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/.well-known/openid-configuration":
            return httpx.Response(200, json=DISCOVERY_PAYLOAD)
        if str(request.url) == DISCOVERY_PAYLOAD["token_endpoint"]:
            return httpx.Response(200, json={"access_token": "the-access-token"})
        if str(request.url) == DISCOVERY_PAYLOAD["userinfo_endpoint"]:
            return httpx.Response(200, json={"sub": sub, "email": email})
        raise AssertionError(f"unexpected request to {request.url}")

    return httpx.MockTransport(handler)


async def test_sso_login_returns_404_when_instance_has_no_oidc_config(
    client: httpx.AsyncClient,
) -> None:
    await _onboard(client)
    response = await client.get("/auth/sso/login")
    assert response.status_code == 404


async def test_sso_callback_returns_404_when_instance_has_no_oidc_config(
    client: httpx.AsyncClient,
) -> None:
    await _onboard(client)
    response = await client.post("/auth/sso/callback", json={"code": "irrelevant"})
    assert response.status_code == 404


async def test_sso_login_redirects_to_the_authorization_endpoint(
    client: httpx.AsyncClient,
) -> None:
    await _onboard(client)
    await _configure_sso()
    app.dependency_overrides[get_oidc_transport] = lambda: _mock_transport(
        sub="user-1", email="user@example.com"
    )

    response = await client.get("/auth/sso/login")

    assert response.status_code == 307
    assert response.headers["location"].startswith(DISCOVERY_PAYLOAD["authorization_endpoint"])


async def test_sso_callback_creates_a_new_member_user_on_first_login(
    client: httpx.AsyncClient,
) -> None:
    await _onboard(client)
    await _configure_sso()
    app.dependency_overrides[get_oidc_transport] = lambda: _mock_transport(
        sub="user-1", email="sso-user@example.com"
    )

    response = await client.post("/auth/sso/callback", json={"code": "the-code"})

    assert response.status_code == 200
    body = response.json()
    assert "access_token" in body
    assert "refresh_token" in body

    session_factory = async_sessionmaker(get_engine(), expire_on_commit=False)
    async with session_factory() as session:
        user = (await session.scalars(select(User).where(User.sso_subject == "user-1"))).one()
        assert user.email == "sso-user@example.com"
        assert user.password_hash is None
        assert user.role == "member"


async def test_sso_callback_reuses_the_existing_user_for_a_known_sub(
    client: httpx.AsyncClient,
) -> None:
    await _onboard(client)
    await _configure_sso()
    app.dependency_overrides[get_oidc_transport] = lambda: _mock_transport(
        sub="user-1", email="sso-user@example.com"
    )

    await client.post("/auth/sso/callback", json={"code": "first-code"})
    await client.post("/auth/sso/callback", json={"code": "second-code"})

    session_factory = async_sessionmaker(get_engine(), expire_on_commit=False)
    async with session_factory() as session:
        users = (await session.scalars(select(User).where(User.sso_subject == "user-1"))).all()
        assert len(users) == 1


def _incomplete_transport(userinfo: dict[str, object]) -> httpx.MockTransport:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/.well-known/openid-configuration":
            return httpx.Response(200, json=DISCOVERY_PAYLOAD)
        if str(request.url) == DISCOVERY_PAYLOAD["token_endpoint"]:
            return httpx.Response(200, json={"access_token": "the-access-token"})
        if str(request.url) == DISCOVERY_PAYLOAD["userinfo_endpoint"]:
            return httpx.Response(200, json=userinfo)
        raise AssertionError(f"unexpected request to {request.url}")

    return httpx.MockTransport(handler)


async def test_signing_in_with_a_known_address_lands_on_the_existing_account(
    client: httpx.AsyncClient,
) -> None:
    """The administrator onboarded with a password, then turned SSO on. Signing in through the
    provider must hand them their own account, not fail on the unique address."""
    await _onboard(client)
    await _configure_sso()
    app.dependency_overrides[get_oidc_transport] = lambda: _mock_transport(
        sub="idp-subject", email=ADMIN_PAYLOAD["email"]
    )

    response = await client.post("/auth/sso/callback", json={"code": "the-code"})

    assert response.status_code == 200
    headers = {"Authorization": f"Bearer {response.json()['access_token']}"}
    me = await client.get("/me", headers=headers)
    assert me.json()["email"] == ADMIN_PAYLOAD["email"]
    assert me.json()["role"] == "admin"
    session_factory = async_sessionmaker(get_engine(), expire_on_commit=False)
    async with session_factory() as session:
        users = list(await session.scalars(select(User)))
    assert len(users) == 1
    assert users[0].sso_subject == "idp-subject"
    # The password they onboarded with still works.
    login = await client.post(
        "/auth/login",
        json={"email": ADMIN_PAYLOAD["email"], "password": ADMIN_PAYLOAD["password"]},
    )
    assert login.status_code == 200


async def test_an_address_already_linked_to_another_subject_is_refused(
    client: httpx.AsyncClient,
) -> None:
    await _onboard(client)
    await _configure_sso()
    app.dependency_overrides[get_oidc_transport] = lambda: _mock_transport(
        sub="first-subject", email=ADMIN_PAYLOAD["email"]
    )
    assert (await client.post("/auth/sso/callback", json={"code": "the-code"})).status_code == 200

    app.dependency_overrides[get_oidc_transport] = lambda: _mock_transport(
        sub="second-subject", email=ADMIN_PAYLOAD["email"]
    )
    response = await client.post("/auth/sso/callback", json={"code": "the-code"})

    assert response.status_code == 409


async def test_a_provider_answering_without_an_email_claim_is_reported(
    client: httpx.AsyncClient,
) -> None:
    """A provider whose email scope was not granted answers without the claim; that used to
    raise a KeyError and surface as an unexplained 500."""
    await _onboard(client)
    await _configure_sso()
    app.dependency_overrides[get_oidc_transport] = lambda: _incomplete_transport(
        {"sub": "idp-subject"}
    )

    response = await client.post("/auth/sso/callback", json={"code": "the-code"})

    assert response.status_code == 502
    assert "email" in response.json()["detail"]


async def test_a_provider_answering_without_a_subject_is_reported(
    client: httpx.AsyncClient,
) -> None:
    await _onboard(client)
    await _configure_sso()
    app.dependency_overrides[get_oidc_transport] = lambda: _incomplete_transport(
        {"email": "someone@example.com"}
    )

    response = await client.post("/auth/sso/callback", json={"code": "the-code"})

    assert response.status_code == 502
