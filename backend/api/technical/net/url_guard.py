import ipaddress
import socket
from collections.abc import Callable, Sequence
from urllib.parse import urlsplit

Resolver = Callable[[str], Sequence[str]]

_ALLOWED_SCHEMES = frozenset({"http", "https"})


class BlockedUrlError(Exception):
    pass


def resolve_with_system(host: str) -> list[str]:
    return [str(info[4][0]) for info in socket.getaddrinfo(host, None, type=socket.SOCK_STREAM)]


def ensure_public_http_url(url: str, *, resolve: Resolver = resolve_with_system) -> None:
    """Rejects a URL the server must not fetch on a user's behalf.

    Anything a reader submits ends up requested from inside the instance's own network, where
    localhost, the private ranges and a cloud provider's metadata endpoint are all reachable and
    none of them are the web. The host is resolved here rather than pattern-matched: a name under
    the attacker's control can point anywhere, and `127.0.0.1` is only the most obvious spelling.
    """
    parts = urlsplit(url)
    if parts.scheme not in _ALLOWED_SCHEMES:
        raise BlockedUrlError(f"unsupported scheme: {parts.scheme or 'none'}")

    host = parts.hostname
    if not host:
        raise BlockedUrlError("URL carries no host")

    try:
        addresses = resolve(host)
    except OSError as exc:
        raise BlockedUrlError(f"{host} does not resolve") from exc
    if not addresses:
        raise BlockedUrlError(f"{host} does not resolve")

    for address in addresses:
        if not _is_public(ipaddress.ip_address(address)):
            raise BlockedUrlError(f"{host} resolves to the non-public address {address}")


def _is_public(address: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
    if isinstance(address, ipaddress.IPv6Address) and address.ipv4_mapped is not None:
        return _is_public(address.ipv4_mapped)
    return not (
        address.is_private
        or address.is_loopback
        or address.is_link_local
        or address.is_multicast
        or address.is_reserved
        or address.is_unspecified
    )


def get_url_resolver() -> Resolver:
    return resolve_with_system
