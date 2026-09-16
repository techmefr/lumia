from collections.abc import AsyncIterator
from unittest.mock import AsyncMock, patch

import httpx
import pyotp
import pytest
from sqlalchemy import update
from sqlalchemy.ext.asyncio import async_sessionmaker

from api.domain.user.models import User
from api.main import app
from api.technical.auth.totp import RECOVERY_CODE_COUNT
from config.database import get_engine
from config.rate_limit import get_rate_limit_config

ADMIN_PAYLOAD = {
    "email": "admin@example.com",
    "username": "admin",
    "password": "correct-horse-battery-staple",
}


@pytest.fixture
async def client(db_schema: None) -> AsyncIterator[httpx.AsyncClient]:
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as async_client:
        yield async_client


def _auth(tokens: dict[str, str]) -> dict[str, str]:
    return {"Authorization": f"Bearer {tokens['access_token']}"}


async def _onboard(client: httpx.AsyncClient) -> dict[str, str]:
    response = await client.post("/onboarding/admin", json=ADMIN_PAYLOAD)
    assert response.status_code == 201
    tokens: dict[str, str] = response.json()
    return tokens


async def _forget_the_spent_step() -> None:
    """Lets a test sign in with the code it just enrolled with, without waiting out a window."""
    session_factory = async_sessionmaker(get_engine(), expire_on_commit=False)
    async with session_factory() as session:
        await session.execute(update(User).values(totp_last_used_step=None))
        await session.commit()


async def _enable_totp(client: httpx.AsyncClient, tokens: dict[str, str]) -> tuple[str, list[str]]:
    enrolment = await client.post("/me/totp/enrolment", headers=_auth(tokens))
    assert enrolment.status_code == 201
    secret = enrolment.json()["secret"]

    confirmed = await client.post(
        "/me/totp", headers=_auth(tokens), json={"code": pyotp.TOTP(secret).now()}
    )
    assert confirmed.status_code == 200
    codes: list[str] = confirmed.json()["recovery_codes"]
    await _forget_the_spent_step()
    return secret, codes


async def _login(client: httpx.AsyncClient, **extra: str) -> httpx.Response:
    return await client.post(
        "/auth/login",
        json={"email": ADMIN_PAYLOAD["email"], "password": ADMIN_PAYLOAD["password"], **extra},
    )


async def _magic_link(client: httpx.AsyncClient, raw_token: str) -> None:
    with (
        patch("api.domain.user.magic_link_service.send_email", new_callable=AsyncMock),
        patch(
            "api.domain.user.magic_link_service.generate_opaque_token",
            return_value=raw_token,
        ),
    ):
        response = await client.post("/auth/magic-link", json={"email": ADMIN_PAYLOAD["email"]})
    assert response.status_code == 202


async def test_a_fresh_account_has_no_second_factor(client: httpx.AsyncClient) -> None:
    tokens = await _onboard(client)

    me = await client.get("/me", headers=_auth(tokens))

    assert me.json()["totp_enabled"] is False
    assert me.json()["recovery_codes_left"] == 0


async def test_enrolment_returns_a_secret_and_a_scannable_uri(client: httpx.AsyncClient) -> None:
    tokens = await _onboard(client)

    response = await client.post("/me/totp/enrolment", headers=_auth(tokens))

    body = response.json()
    assert response.status_code == 201
    assert body["otpauth_uri"].startswith("otpauth://totp/")
    assert body["secret"] in body["otpauth_uri"]


async def test_enrolment_alone_leaves_the_second_factor_off(client: httpx.AsyncClient) -> None:
    tokens = await _onboard(client)
    await client.post("/me/totp/enrolment", headers=_auth(tokens))

    me = await client.get("/me", headers=_auth(tokens))

    assert me.json()["totp_enabled"] is False
    assert (await _login(client)).status_code == 200


async def test_confirming_turns_it_on_and_hands_out_the_recovery_codes(
    client: httpx.AsyncClient,
) -> None:
    tokens = await _onboard(client)

    _, codes = await _enable_totp(client, tokens)

    me = await client.get("/me", headers=_auth(tokens))
    assert len(codes) == RECOVERY_CODE_COUNT
    assert me.json()["totp_enabled"] is True
    assert me.json()["recovery_codes_left"] == RECOVERY_CODE_COUNT


async def test_confirming_with_a_wrong_code_is_refused(client: httpx.AsyncClient) -> None:
    tokens = await _onboard(client)
    await client.post("/me/totp/enrolment", headers=_auth(tokens))

    response = await client.post("/me/totp", headers=_auth(tokens), json={"code": "000000"})

    assert response.status_code == 401
    assert response.json()["detail"] == "invalid_totp_code"
    assert (await client.get("/me", headers=_auth(tokens))).json()["totp_enabled"] is False


async def test_confirming_without_an_enrolment_is_refused(client: httpx.AsyncClient) -> None:
    tokens = await _onboard(client)

    response = await client.post("/me/totp", headers=_auth(tokens), json={"code": "000000"})

    assert response.status_code == 409


async def test_enrolment_is_refused_once_it_is_already_on(client: httpx.AsyncClient) -> None:
    tokens = await _onboard(client)
    await _enable_totp(client, tokens)

    assert (await client.post("/me/totp/enrolment", headers=_auth(tokens))).status_code == 409


async def test_the_password_alone_no_longer_signs_in(client: httpx.AsyncClient) -> None:
    tokens = await _onboard(client)
    await _enable_totp(client, tokens)

    response = await _login(client)

    assert response.status_code == 401
    assert response.json()["detail"] == "totp_required"


async def test_the_password_and_a_live_code_sign_in(client: httpx.AsyncClient) -> None:
    tokens = await _onboard(client)
    secret, _ = await _enable_totp(client, tokens)

    response = await _login(client, totp_code=pyotp.TOTP(secret).now())

    assert response.status_code == 200
    assert response.json()["access_token"]


async def test_a_wrong_code_does_not_sign_in(client: httpx.AsyncClient) -> None:
    tokens = await _onboard(client)
    await _enable_totp(client, tokens)

    response = await _login(client, totp_code="000000")

    assert response.status_code == 401
    assert response.json()["detail"] == "invalid_totp_code"


async def test_a_code_cannot_be_replayed_on_a_second_sign_in(client: httpx.AsyncClient) -> None:
    """A code stays valid for its whole window; an overheard one must not open a second session."""
    tokens = await _onboard(client)
    secret, _ = await _enable_totp(client, tokens)
    code = pyotp.TOTP(secret).now()
    assert (await _login(client, totp_code=code)).status_code == 200

    replayed = await _login(client, totp_code=code)

    assert replayed.status_code == 401
    assert replayed.json()["detail"] == "invalid_totp_code"


async def test_a_wrong_password_is_refused_before_the_code_is_ever_looked_at(
    client: httpx.AsyncClient,
) -> None:
    tokens = await _onboard(client)
    secret, _ = await _enable_totp(client, tokens)

    response = await client.post(
        "/auth/login",
        json={
            "email": ADMIN_PAYLOAD["email"],
            "password": "not-the-password",
            "totp_code": pyotp.TOTP(secret).now(),
        },
    )

    assert response.status_code == 401
    assert response.json().get("detail") != "totp_required"


async def test_a_recovery_code_signs_in_and_is_spent(client: httpx.AsyncClient) -> None:
    tokens = await _onboard(client)
    _, codes = await _enable_totp(client, tokens)

    signed_in = await _login(client, recovery_code=codes[0])

    assert signed_in.status_code == 200
    me = await client.get("/me", headers=_auth(tokens))
    assert me.json()["recovery_codes_left"] == RECOVERY_CODE_COUNT - 1


async def test_a_recovery_code_cannot_be_used_twice(client: httpx.AsyncClient) -> None:
    tokens = await _onboard(client)
    _, codes = await _enable_totp(client, tokens)
    assert (await _login(client, recovery_code=codes[0])).status_code == 200

    replayed = await _login(client, recovery_code=codes[0])

    assert replayed.status_code == 401
    assert replayed.json()["detail"] == "invalid_totp_code"


async def test_a_burst_of_wrong_codes_ends_in_429(client: httpx.AsyncClient) -> None:
    tokens = await _onboard(client)
    await _enable_totp(client, tokens)
    allowance = get_rate_limit_config().totp_max_attempts

    for _ in range(allowance):
        assert (await _login(client, totp_code="000000")).status_code == 401

    assert (await _login(client, totp_code="000000")).status_code == 429


async def test_the_code_allowance_is_tighter_than_the_password_one(
    client: httpx.AsyncClient,
) -> None:
    """Six digits is a million guesses, and the caller already holds the first factor."""
    config = get_rate_limit_config()

    assert config.totp_max_attempts < config.login_max_attempts


async def test_a_magic_link_does_not_walk_past_the_second_factor(
    client: httpx.AsyncClient,
) -> None:
    """A compromised mailbox is the very threat the second factor is there for."""
    tokens = await _onboard(client)
    await _enable_totp(client, tokens)
    await _magic_link(client, "the-raw-token")

    response = await client.post("/auth/magic-link/verify", json={"token": "the-raw-token"})

    assert response.status_code == 401
    assert response.json()["detail"] == "totp_required"


async def test_a_refused_second_factor_leaves_the_magic_link_usable(
    client: httpx.AsyncClient,
) -> None:
    """A link burnt on a mistyped code would send the reader back to their inbox for nothing."""
    tokens = await _onboard(client)
    secret, _ = await _enable_totp(client, tokens)
    await _magic_link(client, "the-raw-token")
    await client.post(
        "/auth/magic-link/verify", json={"token": "the-raw-token", "totp_code": "000000"}
    )

    retried = await client.post(
        "/auth/magic-link/verify",
        json={"token": "the-raw-token", "totp_code": pyotp.TOTP(secret).now()},
    )

    assert retried.status_code == 200


async def test_a_magic_link_with_a_live_code_signs_in(client: httpx.AsyncClient) -> None:
    tokens = await _onboard(client)
    secret, _ = await _enable_totp(client, tokens)
    await _magic_link(client, "the-raw-token")

    response = await client.post(
        "/auth/magic-link/verify",
        json={"token": "the-raw-token", "totp_code": pyotp.TOTP(secret).now()},
    )

    assert response.status_code == 200


async def test_a_password_reset_does_not_walk_past_the_second_factor(
    client: httpx.AsyncClient,
) -> None:
    """The reset hands back a session, so a mailbox alone must not be enough to get one."""
    tokens = await _onboard(client)
    await _enable_totp(client, tokens)
    await _magic_link(client, "the-raw-token")

    response = await client.post(
        "/auth/password-reset",
        json={"token": "the-raw-token", "new_password": "another-horse-battery-staple"},
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "totp_required"


async def test_a_password_reset_with_a_live_code_goes_through(client: httpx.AsyncClient) -> None:
    tokens = await _onboard(client)
    secret, _ = await _enable_totp(client, tokens)
    await _magic_link(client, "the-raw-token")

    response = await client.post(
        "/auth/password-reset",
        json={
            "token": "the-raw-token",
            "new_password": "another-horse-battery-staple",
            "totp_code": pyotp.TOTP(secret).now(),
        },
    )

    assert response.status_code == 200


async def test_disabling_needs_the_password(client: httpx.AsyncClient) -> None:
    tokens = await _onboard(client)
    await _enable_totp(client, tokens)

    response = await client.request("DELETE", "/me/totp", headers=_auth(tokens), json={})

    assert response.status_code == 401
    assert (await client.get("/me", headers=_auth(tokens))).json()["totp_enabled"] is True


async def test_disabling_refuses_a_wrong_password(client: httpx.AsyncClient) -> None:
    tokens = await _onboard(client)
    await _enable_totp(client, tokens)

    response = await client.request(
        "DELETE", "/me/totp", headers=_auth(tokens), json={"password": "not-the-one"}
    )

    assert response.status_code == 401


async def test_disabling_with_the_password_turns_it_off(client: httpx.AsyncClient) -> None:
    tokens = await _onboard(client)
    await _enable_totp(client, tokens)

    response = await client.request(
        "DELETE", "/me/totp", headers=_auth(tokens), json={"password": ADMIN_PAYLOAD["password"]}
    )

    assert response.status_code == 204
    me = await client.get("/me", headers=_auth(tokens))
    assert me.json()["totp_enabled"] is False
    assert me.json()["recovery_codes_left"] == 0
    assert (await _login(client)).status_code == 200


async def test_disabling_what_is_not_on_is_refused(client: httpx.AsyncClient) -> None:
    tokens = await _onboard(client)

    response = await client.request(
        "DELETE", "/me/totp", headers=_auth(tokens), json={"password": ADMIN_PAYLOAD["password"]}
    )

    assert response.status_code == 409


async def test_recovery_codes_can_be_renewed_against_a_live_code(
    client: httpx.AsyncClient,
) -> None:
    tokens = await _onboard(client)
    secret, codes = await _enable_totp(client, tokens)

    response = await client.post(
        "/me/totp/recovery-codes", headers=_auth(tokens), json={"code": pyotp.TOTP(secret).now()}
    )

    assert response.status_code == 200
    fresh: list[str] = response.json()["recovery_codes"]
    assert not set(fresh) & set(codes)
    assert (await _login(client, recovery_code=codes[0])).status_code == 401


async def test_renewing_the_recovery_codes_refuses_a_wrong_code(
    client: httpx.AsyncClient,
) -> None:
    tokens = await _onboard(client)
    _, codes = await _enable_totp(client, tokens)

    response = await client.post(
        "/me/totp/recovery-codes", headers=_auth(tokens), json={"code": "000000"}
    )

    assert response.status_code == 401
    assert (await _login(client, recovery_code=codes[0])).status_code == 200


async def test_renewing_without_a_second_factor_is_refused(client: httpx.AsyncClient) -> None:
    tokens = await _onboard(client)

    response = await client.post(
        "/me/totp/recovery-codes", headers=_auth(tokens), json={"code": "000000"}
    )

    assert response.status_code == 409
