from dataclasses import dataclass
from typing import Any
from urllib.parse import urlencode

import httpx


@dataclass(frozen=True)
class OidcDiscoveryDocument:
    authorization_endpoint: str
    token_endpoint: str
    userinfo_endpoint: str


async def discover(
    issuer: str, *, transport: httpx.AsyncBaseTransport | None = None
) -> OidcDiscoveryDocument:
    async with httpx.AsyncClient(transport=transport) as client:
        response = await client.get(f"{issuer}/.well-known/openid-configuration")
        response.raise_for_status()
        payload = response.json()
    return OidcDiscoveryDocument(
        authorization_endpoint=payload["authorization_endpoint"],
        token_endpoint=payload["token_endpoint"],
        userinfo_endpoint=payload["userinfo_endpoint"],
    )


def build_authorize_url(
    document: OidcDiscoveryDocument, *, client_id: str, redirect_uri: str, state: str
) -> str:
    query = urlencode(
        {
            "response_type": "code",
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "scope": "openid email",
            "state": state,
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
