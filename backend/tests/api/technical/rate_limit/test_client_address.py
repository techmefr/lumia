from collections.abc import Iterator

import pytest
from fastapi import Request

from api.technical.rate_limit.dependencies import client_address
from config.rate_limit import get_rate_limit_config


def _request(forwarded: str | None) -> Request:
    headers = [(b"x-forwarded-for", forwarded.encode())] if forwarded else []
    return Request({"type": "http", "headers": headers, "client": ("10.0.0.9", 1234)})


@pytest.fixture(autouse=True)
def fresh_config() -> Iterator[None]:
    get_rate_limit_config.cache_clear()
    yield
    get_rate_limit_config.cache_clear()


def test_a_single_trusted_proxy_vouches_for_the_last_entry() -> None:
    assert client_address(_request("6.6.6.6, 203.0.113.1")) == "203.0.113.1"


def test_two_trusted_proxies_vouch_for_the_second_entry_from_the_right(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("TRUSTED_PROXY_COUNT", "2")
    assert client_address(_request("6.6.6.6, 203.0.113.1, 10.1.1.1")) == "203.0.113.1"


def test_a_short_chain_falls_back_to_the_first_entry(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TRUSTED_PROXY_COUNT", "3")
    assert client_address(_request("203.0.113.1")) == "203.0.113.1"


def test_a_zero_proxy_count_is_refused(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TRUSTED_PROXY_COUNT", "0")
    with pytest.raises(ValueError):
        get_rate_limit_config()


def test_the_peer_address_is_used_without_the_header() -> None:
    assert client_address(_request(None)) == "10.0.0.9"
