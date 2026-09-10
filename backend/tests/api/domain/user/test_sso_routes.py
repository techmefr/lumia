from collections.abc import AsyncIterator, Callable
from datetime import UTC, datetime, timedelta
from typing import Any
from urllib.parse import parse_qs, urlsplit

import httpx
import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
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

ISSUER = "https://idp.example.com"
CLIENT_ID = "lumia"
DISCOVERY_PAYLOAD = {
    "issuer": ISSUER,
    "authorization_endpoint": f"{ISSUER}/authorize",
    "token_endpoint": f"{ISSUER}/token",
    "userinfo_endpoint": f"{ISSUER}/userinfo",
    "jwks_uri": f"{ISSUER}/jwks",
}

_SIGNING_KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)
_OTHER_KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)


def _jwks(key: rsa.RSAPrivateKey = _SIGNING_KEY) -> dict[str, Any]:
    jwk = jwt.algorithms.RSAAlgorithm.to_jwk(key.public_key(), as_dict=True)
    return {"keys": [{**jwk, "kid": "key-1", "use": "sig"}]}


def _id_token(
    *,
    nonce: str,
    sub: str = "user-1",
    email: str | None = "sso-user@example.com",
    audience: str = CLIENT_ID,
    issuer: str = ISSUER,
    expires_in: timedelta = timedelta(minutes=5),
    key: rsa.RSAPrivateKey = _SIGNING_KEY,
    algorithm: str = "RS256",
) -> str:
    now = datetime.now(UTC)
    claims: dict[str, Any] = {
        "iss": issuer,
        "aud": audience,
        "sub": sub,
        "nonce": nonce,
        "iat": now,
        "exp": now + expires_in,
    }
    if email is not None:
        claims["email"] = email
    return jwt.encode(claims, key, algorithm=algorithm, headers={"kid": "key-1"})


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


async def _configure_sso(issuer: str = ISSUER) -> None:
    session_factory = async_sessionmaker(get_engine(), expire_on_commit=False)
    async with session_factory() as session:
        instance = (await session.scalars(select(Instance))).one()
        instance.oidc_issuer = issuer
        instance.oidc_client_id = CLIENT_ID
        instance.oidc_client_secret_encrypted = encrypt_secret("the-client-secret")
        instance.oidc_redirect_uri = "https://lumia.example.com/auth/sso/callback"
        await session.commit()


def _provider(
    *,
    token_response: dict[str, Any] | None = None,
    userinfo: dict[str, Any] | None = None,
    jwks: dict[str, Any] | None = None,
) -> httpx.MockTransport:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/.well-known/openid-configuration":
            return httpx.Response(200, json=DISCOVERY_PAYLOAD)
        if str(request.url) == DISCOVERY_PAYLOAD["jwks_uri"]:
            return httpx.Response(200, json=jwks if jwks is not None else _jwks())
        if str(request.url) == DISCOVERY_PAYLOAD["token_endpoint"]:
            return httpx.Response(200, json=token_response or {})
        if str(request.url) == DISCOVERY_PAYLOAD["userinfo_endpoint"]:
            if userinfo is None:
                raise AssertionError("the identity must not be read from /userinfo")
            return httpx.Response(200, json=userinfo)
        raise AssertionError(f"unexpected request to {request.url}")

    return httpx.MockTransport(handler)


def _use(transport: httpx.MockTransport) -> None:
    app.dependency_overrides[get_oidc_transport] = lambda: transport


async def _start_login(client: httpx.AsyncClient) -> tuple[str, str]:
    """Walks the browser's first leg and returns the state and nonce the provider will echo."""
    _use(_provider())
    response = await client.get("/auth/sso/login")
    assert response.status_code == 307
    query = parse_qs(urlsplit(response.headers["location"]).query)
    return query["state"][0], query["nonce"][0]


async def _callback(
    client: httpx.AsyncClient,
    *,
    state: str,
    id_token: str | None,
    userinfo: dict[str, Any] | None = None,
    access_token: str = "the-access-token",
) -> httpx.Response:
    token_response: dict[str, Any] = {"access_token": access_token}
    if id_token is not None:
        token_response["id_token"] = id_token
    _use(_provider(token_response=token_response, userinfo=userinfo))
    return await client.post("/auth/sso/callback", json={"code": "the-code", "state": state})


async def _sso_users() -> list[User]:
    session_factory = async_sessionmaker(get_engine(), expire_on_commit=False)
    async with session_factory() as session:
        return list((await session.scalars(select(User).where(User.sso_subject.isnot(None)))).all())


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
    response = await client.post(
        "/auth/sso/callback", json={"code": "irrelevant", "state": "irrelevant"}
    )
    assert response.status_code == 404


async def test_sso_login_redirects_to_the_authorization_endpoint(
    client: httpx.AsyncClient,
) -> None:
    await _onboard(client)
    await _configure_sso()

    _use(_provider())
    response = await client.get("/auth/sso/login")

    assert response.status_code == 307
    assert response.headers["location"].startswith(DISCOVERY_PAYLOAD["authorization_endpoint"])


async def test_sso_login_sends_a_state_and_a_nonce(client: httpx.AsyncClient) -> None:
    await _onboard(client)
    await _configure_sso()

    state, nonce = await _start_login(client)

    assert state
    assert nonce
    assert state != nonce


async def test_two_logins_get_two_different_states(client: httpx.AsyncClient) -> None:
    await _onboard(client)
    await _configure_sso()

    first, _ = await _start_login(client)
    second, _ = await _start_login(client)

    assert first != second


async def test_sso_login_refuses_an_issuer_that_is_not_https(client: httpx.AsyncClient) -> None:
    await _onboard(client)
    await _configure_sso(issuer="http://idp.example.com")

    _use(_provider())
    response = await client.get("/auth/sso/login")

    assert response.status_code == 400


async def test_sso_callback_creates_a_new_member_user_on_first_login(
    client: httpx.AsyncClient,
) -> None:
    await _onboard(client)
    await _configure_sso()
    state, nonce = await _start_login(client)

    response = await _callback(client, state=state, id_token=_id_token(nonce=nonce))

    assert response.status_code == 200
    body = response.json()
    assert "access_token" in body
    assert "refresh_token" in body
    users = await _sso_users()
    assert [(user.sso_subject, user.email, user.role) for user in users] == [
        ("user-1", "sso-user@example.com", "member")
    ]
    assert users[0].password_hash is None


async def test_sso_callback_reuses_the_existing_user_for_a_known_sub(
    client: httpx.AsyncClient,
) -> None:
    await _onboard(client)
    await _configure_sso()
    for _ in range(2):
        state, nonce = await _start_login(client)
        assert (
            await _callback(client, state=state, id_token=_id_token(nonce=nonce))
        ).status_code == 200

    assert len(await _sso_users()) == 1


async def test_sso_callback_without_a_state_is_rejected_by_the_schema(
    client: httpx.AsyncClient,
) -> None:
    await _onboard(client)
    await _configure_sso()

    response = await client.post("/auth/sso/callback", json={"code": "the-code"})

    assert response.status_code == 422


async def test_sso_callback_refuses_a_state_nobody_issued(client: httpx.AsyncClient) -> None:
    """This is the CSRF guard: a code delivered to a browser that started no login is refused."""
    await _onboard(client)
    await _configure_sso()
    _, nonce = await _start_login(client)

    response = await _callback(client, state="forged-state", id_token=_id_token(nonce=nonce))

    assert response.status_code == 401
    assert await _sso_users() == []


async def test_a_state_can_only_be_used_once(client: httpx.AsyncClient) -> None:
    await _onboard(client)
    await _configure_sso()
    state, nonce = await _start_login(client)
    await _callback(client, state=state, id_token=_id_token(nonce=nonce))

    replay = await _callback(client, state=state, id_token=_id_token(nonce=nonce))

    assert replay.status_code == 401


async def test_sso_callback_refuses_an_id_token_bound_to_another_login(
    client: httpx.AsyncClient,
) -> None:
    await _onboard(client)
    await _configure_sso()
    state, _ = await _start_login(client)
    _, other_nonce = await _start_login(client)

    response = await _callback(client, state=state, id_token=_id_token(nonce=other_nonce))

    assert response.status_code == 401
    assert await _sso_users() == []


async def test_sso_callback_refuses_a_token_response_without_an_id_token(
    client: httpx.AsyncClient,
) -> None:
    await _onboard(client)
    await _configure_sso()
    state, _ = await _start_login(client)

    response = await _callback(client, state=state, id_token=None)

    assert response.status_code == 401


@pytest.mark.parametrize(
    "make_id_token",
    [
        pytest.param(
            lambda nonce: _id_token(nonce=nonce, key=_OTHER_KEY), id="signed by another key"
        ),
        pytest.param(
            lambda nonce: _id_token(nonce=nonce, audience="another-client"), id="wrong audience"
        ),
        pytest.param(
            lambda nonce: _id_token(nonce=nonce, issuer="https://evil.example.com"),
            id="wrong issuer",
        ),
        pytest.param(
            lambda nonce: _id_token(nonce=nonce, expires_in=timedelta(minutes=-1)), id="expired"
        ),
    ],
)
async def test_sso_callback_refuses_an_id_token_that_does_not_check_out(
    client: httpx.AsyncClient, make_id_token: Callable[[str], str]
) -> None:
    await _onboard(client)
    await _configure_sso()
    state, nonce = await _start_login(client)

    response = await _callback(client, state=state, id_token=make_id_token(nonce))

    assert response.status_code == 401
    assert await _sso_users() == []


async def test_sso_callback_refuses_an_id_token_signed_with_a_symmetric_algorithm(
    client: httpx.AsyncClient,
) -> None:
    """Alg confusion: an accepted HS256 header turns the provider's public key into a shared
    secret, and the public key is public — anyone could then mint an id_token."""
    await _onboard(client)
    await _configure_sso()
    state, nonce = await _start_login(client)
    forged = jwt.encode(
        {
            "iss": ISSUER,
            "aud": CLIENT_ID,
            "sub": "intruder",
            "nonce": nonce,
            "iat": datetime.now(UTC),
            "exp": datetime.now(UTC) + timedelta(minutes=5),
        },
        "whatever-secret-the-attacker-picks",
        algorithm="HS256",
        headers={"kid": "key-1"},
    )

    response = await _callback(client, state=state, id_token=forged)

    assert response.status_code == 401
    assert await _sso_users() == []


async def test_the_identity_comes_from_the_signed_token_not_from_userinfo(
    client: httpx.AsyncClient,
) -> None:
    """/userinfo is an unsigned http answer: it must not be able to name who just logged in."""
    await _onboard(client)
    await _configure_sso()
    state, nonce = await _start_login(client)

    await _callback(
        client,
        state=state,
        id_token=_id_token(nonce=nonce, sub="the-real-subject"),
        userinfo={"sub": "someone-else", "email": "attacker@example.com"},
    )

    assert [user.sso_subject for user in await _sso_users()] == ["the-real-subject"]


async def test_userinfo_fills_in_an_email_the_id_token_left_out(
    client: httpx.AsyncClient,
) -> None:
    await _onboard(client)
    await _configure_sso()
    state, nonce = await _start_login(client)

    response = await _callback(
        client,
        state=state,
        id_token=_id_token(nonce=nonce, email=None),
        userinfo={"sub": "ignored", "email": "from-userinfo@example.com"},
    )

    assert response.status_code == 200
    assert [user.email for user in await _sso_users()] == ["from-userinfo@example.com"]


async def test_sso_callback_refuses_a_login_with_no_email_anywhere(
    client: httpx.AsyncClient,
) -> None:
    await _onboard(client)
    await _configure_sso()
    state, nonce = await _start_login(client)

    response = await _callback(
        client,
        state=state,
        id_token=_id_token(nonce=nonce, email=None),
        userinfo={"sub": "user-1"},
    )

    assert response.status_code == 401
