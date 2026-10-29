import httpx
import pytest

from api.technical.net.pinned_transport import PinnedAddressTransport, guarded_transport
from api.technical.net.url_guard import BlockedUrlError


class _Recording(httpx.AsyncBaseTransport):
    def __init__(self) -> None:
        self.requests: list[httpx.Request] = []

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        return httpx.Response(200, text="ok")


async def test_the_connection_goes_to_the_validated_address_with_the_name_kept() -> None:
    inner = _Recording()
    transport = PinnedAddressTransport(inner=inner, resolve=lambda _host: ["93.184.216.34"])

    async with httpx.AsyncClient(transport=transport) as client:
        response = await client.get("https://example.com/a?b=1")

    assert response.status_code == 200
    sent = inner.requests[0]
    assert sent.url.host == "93.184.216.34"
    assert sent.url.path == "/a"
    assert sent.url.query == b"b=1"
    assert sent.headers["host"] == "example.com"
    assert sent.extensions["sni_hostname"] == "example.com"


async def test_a_second_resolution_that_rebinds_is_never_consulted() -> None:
    answers = iter([["93.184.216.34"], ["127.0.0.1"]])
    inner = _Recording()
    transport = PinnedAddressTransport(inner=inner, resolve=lambda _host: next(answers))

    async with httpx.AsyncClient(transport=transport) as client:
        await client.get("https://rebind.example/a")

    assert [request.url.host for request in inner.requests] == ["93.184.216.34"]


async def test_a_name_resolving_to_a_private_address_is_not_connected_to() -> None:
    inner = _Recording()
    transport = PinnedAddressTransport(inner=inner, resolve=lambda _host: ["127.0.0.1"])

    async with httpx.AsyncClient(transport=transport) as client:
        with pytest.raises(BlockedUrlError):
            await client.get("https://evil.example/a")

    assert inner.requests == []


async def test_a_literal_address_gets_no_server_name_override() -> None:
    inner = _Recording()
    transport = PinnedAddressTransport(inner=inner, resolve=lambda host: [host])

    async with httpx.AsyncClient(transport=transport) as client:
        await client.get("http://93.184.216.34/a")

    assert "sni_hostname" not in inner.requests[0].extensions


def test_an_injected_transport_is_used_as_is() -> None:
    injected = httpx.MockTransport(lambda _request: httpx.Response(200))

    assert guarded_transport(injected, lambda _host: ["93.184.216.34"]) is injected


def test_without_an_injected_transport_the_address_is_pinned() -> None:
    assert isinstance(
        guarded_transport(None, lambda _host: ["93.184.216.34"]), PinnedAddressTransport
    )
