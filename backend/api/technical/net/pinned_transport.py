import asyncio
from types import TracebackType
from typing import Self

import httpx

from api.technical.net.url_guard import Resolver, resolve_public_addresses, resolve_with_system


class PinnedAddressTransport(httpx.AsyncBaseTransport):
    """Connects to the address that was validated, not to whatever the name resolves to next.

    Checking a host and then letting the HTTP client resolve it again leaves a window in which a
    name under the attacker's control answers with a public address for the check and with an
    internal one for the connection. Here the request is rewritten to the validated address, with
    the original name kept in the Host header and as the TLS server name so certificates still
    match.
    """

    def __init__(
        self,
        *,
        inner: httpx.AsyncBaseTransport | None = None,
        resolve: Resolver = resolve_with_system,
    ) -> None:
        self._inner = inner or httpx.AsyncHTTPTransport()
        self._resolve = resolve

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        host = request.url.host
        addresses = await asyncio.to_thread(
            resolve_public_addresses, str(request.url), resolve=self._resolve
        )
        pinned = addresses[0]
        extensions = dict(request.extensions)
        if pinned != host:
            extensions["sni_hostname"] = host
        rewritten = httpx.Request(
            request.method,
            request.url.copy_with(host=pinned),
            headers=request.headers,
            stream=request.stream,
            extensions=extensions,
        )
        return await self._inner.handle_async_request(rewritten)

    async def aclose(self) -> None:
        await self._inner.aclose()

    async def __aenter__(self) -> Self:
        await self._inner.__aenter__()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None = None,
        exc_value: BaseException | None = None,
        traceback: TracebackType | None = None,
    ) -> None:
        await self._inner.__aexit__(exc_type, exc_value, traceback)


def guarded_transport(
    transport: httpx.AsyncBaseTransport | None, resolve: Resolver
) -> httpx.AsyncBaseTransport:
    if transport is not None:
        return transport
    return PinnedAddressTransport(resolve=resolve)
