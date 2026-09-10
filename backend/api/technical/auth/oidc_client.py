from dataclasses import dataclass
from typing import Any
from urllib.parse import urlencode, urlsplit

import httpx
import jwt


class InsecureIssuerError(Exception):
    pass


class InvalidIdTokenError(Exception):
    pass


def get_oidc_transport() -> httpx.AsyncBaseTransport | None:
    return None


@dataclass(frozen=True)
class OidcDiscoveryDocument:
    issuer: str
    authorization_endpoint: str
    token_endpoint: str
    userinfo_endpoint: str
    jwks_uri: str


async def discover(
    issuer: str, *, transport: httpx.AsyncBaseTransport | None = None
) -> OidcDiscoveryDocument:
    # Discovery hands out the endpoints every later call trusts, and the client secret travels to
    # the token endpoint it names: over plain http anyone on the path rewrites the whole flow.
    if urlsplit(issuer).scheme != "https":
        raise InsecureIssuerError(f"the OIDC issuer must be an https URL, got {issuer!r}")
    async with httpx.AsyncClient(transport=transport) as client:
        response = await client.get(f"{issuer}/.well-known/openid-configuration")
        response.raise_for_status()
        payload = response.json()
    return OidcDiscoveryDocument(
        issuer=payload.get("issuer", issuer),
        authorization_endpoint=payload["authorization_endpoint"],
        token_endpoint=payload["token_endpoint"],
        userinfo_endpoint=payload["userinfo_endpoint"],
        jwks_uri=payload["jwks_uri"],
    )


def build_authorize_url(
    document: OidcDiscoveryDocument,
    *,
    client_id: str,
    redirect_uri: str,
    state: str,
    nonce: str,
) -> str:
    query = urlencode(
        {
            "response_type": "code",
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "scope": "openid email",
            "state": state,
            "nonce": nonce,
        }
    )
    return f"{document.authorization_endpoint}?{query}"


async def exchange_code_for_tokens(
    document: OidcDiscoveryDocument,
    *,
    client_id: str,
    client_secret: str,
    redirect_uri: str,
    code: str,
    transport: httpx.AsyncBaseTransport | None = None,
) -> dict[str, Any]:
    async with httpx.AsyncClient(transport=transport) as client:
        response = await client.post(
            document.token_endpoint,
            data={
                "grant_type": "authorization_code",
                "client_id": client_id,
                "client_secret": client_secret,
                "redirect_uri": redirect_uri,
                "code": code,
            },
        )
        response.raise_for_status()
        return dict(response.json())


async def fetch_jwks(
    document: OidcDiscoveryDocument, *, transport: httpx.AsyncBaseTransport | None = None
) -> dict[str, Any]:
    async with httpx.AsyncClient(transport=transport) as client:
        response = await client.get(document.jwks_uri)
        response.raise_for_status()
        return dict(response.json())


async def fetch_userinfo(
    document: OidcDiscoveryDocument,
    *,
    access_token: str,
    transport: httpx.AsyncBaseTransport | None = None,
) -> dict[str, Any]:
    async with httpx.AsyncClient(transport=transport) as client:
        response = await client.get(
            document.userinfo_endpoint,
            headers={"Authorization": f"Bearer {access_token}"},
        )
        response.raise_for_status()
        return dict(response.json())


def verify_id_token(
    id_token: str,
    *,
    jwks: dict[str, Any],
    issuer: str,
    client_id: str,
    nonce: str,
) -> dict[str, Any]:
    """Checks the id_token's signature and claims and returns them.

    This is what makes the identity trustworthy: `/userinfo` is only an http answer, and on its own
    it proves nothing about who the provider actually authenticated. The nonce ties the token to the
    login this browser started, so an id_token captured from another session cannot be replayed.
    """
    header = jwt.get_unverified_header(id_token)
    # The token's own header must not be able to pick a symmetric algorithm: with "HS256" the
    # public key we just fetched would double as the shared secret, and anyone could sign.
    if header.get("alg") not in _SUPPORTED_ALGORITHMS:
        raise InvalidIdTokenError(f"unsupported id_token algorithm {header.get('alg')!r}")
    try:
        key = _signing_key(id_token, jwks)
        claims = jwt.decode(
            id_token,
            key.key,
            algorithms=[str(header["alg"])],
            audience=client_id,
            issuer=issuer,
            options={"require": ["exp", "iat", "sub"]},
        )
    except jwt.PyJWTError as exc:
        raise InvalidIdTokenError(str(exc)) from exc

    if claims.get("nonce") != nonce:
        raise InvalidIdTokenError("the id_token carries no matching nonce")
    return dict(claims)


_SUPPORTED_ALGORITHMS = ["RS256", "RS384", "RS512", "ES256", "ES384", "PS256"]


def _signing_key(id_token: str, jwks: dict[str, Any]) -> jwt.PyJWK:
    key_set = jwt.PyJWKSet.from_dict(jwks)
    usable = [key for key in key_set.keys if key.public_key_use in ("sig", None)]
    kid = jwt.get_unverified_header(id_token).get("kid")
    if kid is not None:
        for key in usable:
            if key.key_id == kid:
                return key
        raise InvalidIdTokenError(f"the provider published no signing key {kid!r}")
    # A single-key provider may omit the kid; more than one and there is no way to tell which
    # signed this token, so refuse rather than trying each in turn.
    if len(usable) == 1:
        return usable[0]
    raise InvalidIdTokenError("the id_token names no key and the provider publishes several")
