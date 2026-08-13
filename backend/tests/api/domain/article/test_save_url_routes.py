from collections.abc import AsyncIterator
from datetime import UTC, datetime

import httpx
import pytest

from api.main import app
from worker.technical.content_extraction import (
    ExtractedPage,
    PageFetchError,
    get_page_extractor,
)

ADMIN_PAYLOAD = {
    "email": "admin@example.com",
    "username": "admin",
    "password": "correct-horse-battery-staple",
}

PAGE = ExtractedPage(
    title="Un titre extrait",
    content="<p>Le corps de l'article.</p>",
    image_url="https://example.com/cover.jpg",
    author="Jane Doe",
    published_at=datetime(2026, 8, 1, tzinfo=UTC),
)


class _FakePageExtractor:
    def __init__(self, page: ExtractedPage | None = None) -> None:
        self._page = page
        self.calls: list[str] = []

    async def fetch(self, url: str) -> ExtractedPage:
        self.calls.append(url)
        if self._page is None:
            raise PageFetchError("unreadable")
        return self._page


@pytest.fixture
async def client(db_schema: None) -> AsyncIterator[httpx.AsyncClient]:
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as async_client:
        yield async_client
    app.dependency_overrides.clear()


async def _headers(client: httpx.AsyncClient) -> dict[str, str]:
    response = await client.post("/onboarding/admin", json=ADMIN_PAYLOAD)
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def _use(extractor: _FakePageExtractor) -> None:
    app.dependency_overrides[get_page_extractor] = lambda: extractor


async def test_save_url_creates_a_readable_article(client: httpx.AsyncClient) -> None:
    headers = await _headers(client)
    _use(_FakePageExtractor(PAGE))

    response = await client.post(
        "/articles/save-url", json={"url": "https://example.com/post"}, headers=headers
    )
    assert response.status_code == 201
    body = response.json()
    assert body["title"] == "Un titre extrait"
    assert body["author_name"] == "Jane Doe"
    assert body["image_url"] == "https://example.com/cover.jpg"
    assert body["source_label"] == "Enregistrés"


async def test_saved_url_appears_in_the_saved_list(client: httpx.AsyncClient) -> None:
    headers = await _headers(client)
    _use(_FakePageExtractor(PAGE))
    await client.post(
        "/articles/save-url", json={"url": "https://example.com/post"}, headers=headers
    )

    response = await client.get("/articles/saved", headers=headers)
    assert [article["title"] for article in response.json()] == ["Un titre extrait"]


async def test_saving_the_same_url_twice_does_not_duplicate(client: httpx.AsyncClient) -> None:
    headers = await _headers(client)
    extractor = _FakePageExtractor(PAGE)
    _use(extractor)

    first = await client.post(
        "/articles/save-url", json={"url": "https://example.com/post"}, headers=headers
    )
    second = await client.post(
        "/articles/save-url", json={"url": "https://example.com/post"}, headers=headers
    )

    assert first.json()["id"] == second.json()["id"]
    assert len((await client.get("/articles/saved", headers=headers)).json()) == 1
    # The page is only fetched for the first save.
    assert extractor.calls == ["https://example.com/post"]


async def test_save_url_reuses_a_single_manual_feed(client: httpx.AsyncClient) -> None:
    headers = await _headers(client)
    _use(_FakePageExtractor(PAGE))

    await client.post("/articles/save-url", json={"url": "https://a.test/1"}, headers=headers)
    await client.post("/articles/save-url", json={"url": "https://a.test/2"}, headers=headers)

    feeds = (await client.get("/feeds", headers=headers)).json()
    manual = [feed for feed in feeds if feed["source_type"] == "manual"]
    assert len(manual) == 1


async def test_save_url_on_an_unreadable_page_returns_400(client: httpx.AsyncClient) -> None:
    headers = await _headers(client)
    _use(_FakePageExtractor(None))

    response = await client.post(
        "/articles/save-url", json={"url": "https://example.com/broken"}, headers=headers
    )
    assert response.status_code == 400
    assert (await client.get("/articles/saved", headers=headers)).json() == []


async def test_save_url_requires_authentication(client: httpx.AsyncClient) -> None:
    _use(_FakePageExtractor(PAGE))
    response = await client.post("/articles/save-url", json={"url": "https://example.com/post"})
    assert response.status_code == 401
