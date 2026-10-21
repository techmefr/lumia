import httpx

from api.technical.net.image_fetcher import GuardedImageFetcher

PUBLIC = ["93.184.216.34"]


def _fetcher(
    handler: httpx.MockTransport, *, resolves_to: list[str] | None = None
) -> GuardedImageFetcher:
    addresses = resolves_to if resolves_to is not None else PUBLIC
    return GuardedImageFetcher(transport=handler, resolve=lambda _host: addresses)


async def test_it_returns_the_image_and_its_media_type() -> None:
    transport = httpx.MockTransport(
        lambda _request: httpx.Response(200, content=b"png", headers={"content-type": "image/png"})
    )

    image = await _fetcher(transport).fetch("https://example.com/a.png")

    assert image is not None
    assert image.media_type == "image/png"
    assert image.data == b"png"


async def test_the_media_type_parameters_are_ignored() -> None:
    transport = httpx.MockTransport(
        lambda _request: httpx.Response(
            200, content=b"jpg", headers={"content-type": "Image/JPEG; charset=binary"}
        )
    )

    image = await _fetcher(transport).fetch("https://example.com/a")

    assert image is not None
    assert image.media_type == "image/jpeg"


async def test_it_refuses_a_page_that_is_not_an_image() -> None:
    transport = httpx.MockTransport(
        lambda _request: httpx.Response(
            200, content=b"<html>", headers={"content-type": "text/html"}
        )
    )

    assert await _fetcher(transport).fetch("https://example.com/a") is None


async def test_it_refuses_an_svg_because_it_can_carry_a_script() -> None:
    transport = httpx.MockTransport(
        lambda _request: httpx.Response(
            200, content=b"<svg/>", headers={"content-type": "image/svg+xml"}
        )
    )

    assert await _fetcher(transport).fetch("https://example.com/a.svg") is None


async def test_it_gives_up_on_an_image_over_the_size_cap() -> None:
    transport = httpx.MockTransport(
        lambda _request: httpx.Response(
            200, content=b"x" * (6 * 1024 * 1024), headers={"content-type": "image/png"}
        )
    )

    assert await _fetcher(transport).fetch("https://example.com/big.png") is None


async def test_it_never_calls_a_host_that_resolves_to_a_private_address() -> None:
    calls: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(str(request.url))
        return httpx.Response(200, content=b"png", headers={"content-type": "image/png"})

    fetcher = _fetcher(httpx.MockTransport(handler), resolves_to=["127.0.0.1"])

    assert await fetcher.fetch("https://internal.example/a.png") is None
    assert calls == []


async def test_it_follows_a_redirect_to_another_public_image() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/old.png":
            return httpx.Response(302, headers={"location": "/new.png"})
        return httpx.Response(200, content=b"png", headers={"content-type": "image/png"})

    image = await _fetcher(httpx.MockTransport(handler)).fetch("https://example.com/old.png")

    assert image is not None
    assert image.data == b"png"


async def test_a_redirect_to_a_private_address_is_refused_on_the_second_hop() -> None:
    resolved: list[str] = []

    def resolve(host: str) -> list[str]:
        resolved.append(host)
        return ["127.0.0.1"] if host == "internal.example" else PUBLIC

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.host == "example.com":
            return httpx.Response(302, headers={"location": "https://internal.example/secret.png"})
        return httpx.Response(200, content=b"png", headers={"content-type": "image/png"})

    fetcher = GuardedImageFetcher(transport=httpx.MockTransport(handler), resolve=resolve)

    assert await fetcher.fetch("https://example.com/a.png") is None
    assert resolved == ["example.com", "internal.example"]


async def test_a_redirect_loop_is_given_up_on() -> None:
    transport = httpx.MockTransport(
        lambda _request: httpx.Response(302, headers={"location": "/a.png"})
    )

    assert await _fetcher(transport).fetch("https://example.com/a.png") is None


async def test_a_server_error_is_not_an_exception_for_the_caller() -> None:
    transport = httpx.MockTransport(lambda _request: httpx.Response(500))

    assert await _fetcher(transport).fetch("https://example.com/a.png") is None
