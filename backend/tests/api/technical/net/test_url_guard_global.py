import pytest

from api.technical.net.url_guard import BlockedUrlError, ensure_public_http_url


@pytest.mark.parametrize(
    "address", ["100.64.0.1", "100.127.255.254", "198.18.0.1", "::ffff:100.64.0.1"]
)
def test_shared_and_benchmark_ranges_are_not_public(address: str) -> None:
    with pytest.raises(BlockedUrlError):
        ensure_public_http_url("https://example.com/", resolve=lambda _host: [address])
