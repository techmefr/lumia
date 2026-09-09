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
