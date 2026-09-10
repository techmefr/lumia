import socket
from collections.abc import Callable

import pytest

from api.technical.net.url_guard import (
    BlockedUrlError,
    ensure_public_http_url,
    resolve_with_system,
)


def _resolving_to(*addresses: str) -> Callable[[str], list[str]]:
    def resolve(host: str) -> list[str]:
        return list(addresses)

    return resolve


def test_a_public_address_is_allowed() -> None:
    ensure_public_http_url("https://example.com/article", resolve=_resolving_to("93.184.216.34"))


@pytest.mark.parametrize(
    "url",
    [
        "file:///etc/passwd",
        "gopher://example.com/",
        "ftp://example.com/",
        "//example.com/no-scheme",
        "https:///no-host",
    ],
)
def test_only_http_urls_with_a_host_are_allowed(url: str) -> None:
    with pytest.raises(BlockedUrlError):
        ensure_public_http_url(url, resolve=_resolving_to("93.184.216.34"))


@pytest.mark.parametrize(
    "address",
    [
        "127.0.0.1",
        "10.0.0.5",
        "172.16.3.4",
        "192.168.1.20",
        "169.254.169.254",
        "0.0.0.0",
        "224.0.0.1",
        "::1",
        "fe80::1",
        "fc00::1",
        "::ffff:127.0.0.1",
    ],
)
def test_a_host_resolving_off_the_public_internet_is_blocked(address: str) -> None:
    with pytest.raises(BlockedUrlError):
        ensure_public_http_url("http://internal.test/", resolve=_resolving_to(address))


def test_a_single_private_address_blocks_a_multi_homed_host() -> None:
    with pytest.raises(BlockedUrlError):
        ensure_public_http_url(
            "http://mixed.test/", resolve=_resolving_to("93.184.216.34", "127.0.0.1")
        )


def test_a_host_that_does_not_resolve_is_blocked() -> None:
    def resolve(host: str) -> list[str]:
        raise socket.gaierror("no such host")

    with pytest.raises(BlockedUrlError):
        ensure_public_http_url("http://nowhere.test/", resolve=resolve)


def test_an_empty_resolution_is_blocked() -> None:
    with pytest.raises(BlockedUrlError):
        ensure_public_http_url("http://nowhere.test/", resolve=_resolving_to())


def test_the_system_resolver_returns_addresses_for_localhost() -> None:
    assert resolve_with_system("localhost")
