import httpx
import pytest

from api.technical.auth.oidc_client import (
    InsecureIssuerError,
    OidcDiscoveryDocument,
    build_authorize_url,
    discover,
    exchange_code_for_tokens,
    fetch_jwks,
    fetch_userinfo,
)

DISCOVERY_PAYLOAD = {
    "issuer": "https://idp.example.com",
    "authorization_endpoint": "https://idp.example.com/authorize",
    "token_endpoint": "https://idp.example.com/token",
    "userinfo_endpoint": "https://idp.example.com/userinfo",
    "jwks_uri": "https://idp.example.com/jwks",
}


async def test_discover_fetches_the_well_known_document() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url == "https://idp.example.com/.well-known/openid-configuration"
        return httpx.Response(200, json=DISCOVERY_PAYLOAD)

    document = await discover("https://idp.example.com", transport=httpx.MockTransport(handler))
    assert document.authorization_endpoint == DISCOVERY_PAYLOAD["authorization_endpoint"]
    assert document.token_endpoint == DISCOVERY_PAYLOAD["token_endpoint"]
    assert document.userinfo_endpoint == DISCOVERY_PAYLOAD["userinfo_endpoint"]
    assert document.jwks_uri == DISCOVERY_PAYLOAD["jwks_uri"]


def test_build_authorize_url_includes_client_id_redirect_uri_state_and_nonce() -> None:
    document = OidcDiscoveryDocument(**DISCOVERY_PAYLOAD)
    url = build_authorize_url(
        document,
        client_id="lumia",
        redirect_uri="https://lumia.example.com/auth/sso/callback",
        state="xyz",
        nonce="abc",
    )
    assert url.startswith(DISCOVERY_PAYLOAD["authorization_endpoint"])
    assert "client_id=lumia" in url
    assert "state=xyz" in url
    assert "nonce=abc" in url
    assert "redirect_uri=https%3A%2F%2Flumia.example.com%2Fauth%2Fsso%2Fcallback" in url


async def test_exchange_code_for_tokens_posts_to_the_token_endpoint() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url == DISCOVERY_PAYLOAD["token_endpoint"]
        return httpx.Response(200, json={"access_token": "the-access-token"})

    document = OidcDiscoveryDocument(**DISCOVERY_PAYLOAD)
    tokens = await exchange_code_for_tokens(
        document,
        client_id="lumia",
        client_secret="shh",
        redirect_uri="https://lumia.example.com/auth/sso/callback",
        code="the-code",
        transport=httpx.MockTransport(handler),
    )
    assert tokens["access_token"] == "the-access-token"


async def test_fetch_userinfo_sends_the_bearer_token() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["authorization"] == "Bearer the-access-token"
        return httpx.Response(200, json={"sub": "user-123", "email": "user@example.com"})

    document = OidcDiscoveryDocument(**DISCOVERY_PAYLOAD)
    userinfo = await fetch_userinfo(
        document, access_token="the-access-token", transport=httpx.MockTransport(handler)
    )
    assert userinfo["sub"] == "user-123"


async def test_discover_raises_on_an_http_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404)

    with pytest.raises(httpx.HTTPStatusError):
        await discover("https://idp.example.com", transport=httpx.MockTransport(handler))


async def test_discover_refuses_an_issuer_that_is_not_https() -> None:
    """The client secret travels to the endpoint discovery names, so plain http is a non-starter."""

    def handler(request: httpx.Request) -> httpx.Response:
        raise AssertionError("no request should leave for an http issuer")

    with pytest.raises(InsecureIssuerError):
        await discover("http://idp.example.com", transport=httpx.MockTransport(handler))


async def test_fetch_jwks_reads_the_key_set_the_document_names() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert str(request.url) == DISCOVERY_PAYLOAD["jwks_uri"]
        return httpx.Response(200, json={"keys": [{"kid": "key-1"}]})

    document = OidcDiscoveryDocument(**DISCOVERY_PAYLOAD)
    jwks = await fetch_jwks(document, transport=httpx.MockTransport(handler))

    assert jwks["keys"] == [{"kid": "key-1"}]
