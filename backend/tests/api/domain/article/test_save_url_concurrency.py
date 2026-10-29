import asyncio
from collections.abc import AsyncIterator
from datetime import UTC, datetime

import httpx
import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker

from api.domain.article.models import Article, Author
from api.domain.feed.models import Feed, SourceType
from api.main import app
from config.database import get_engine
from worker.technical.content_extraction import ExtractedPage, get_page_extractor

ADMIN_PAYLOAD = {
    "email": "admin@example.com",
    "username": "admin",
    "password": "correct-horse-battery-staple",
}


class _SlowExtractor:
    async def fetch(self, url: str) -> ExtractedPage:
        await asyncio.sleep(0.2)
        return ExtractedPage(
            title="Titre",
            content="<p>Corps</p>",
            author="Jane Doe",
            published_at=datetime(2026, 8, 1, tzinfo=UTC),
        )


@pytest.fixture
async def client(db_schema: None) -> AsyncIterator[httpx.AsyncClient]:
    app.dependency_overrides[get_page_extractor] = lambda: _SlowExtractor()
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as async_client:
        yield async_client
    app.dependency_overrides.clear()


async def _headers(client: httpx.AsyncClient) -> dict[str, str]:
    response = await client.post("/onboarding/admin", json=ADMIN_PAYLOAD)
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


async def _count(model: type) -> int:
    async with async_sessionmaker(get_engine())() as session:
        return int(await session.scalar(select(func.count()).select_from(model)) or 0)


async def test_concurrent_saves_of_different_urls_share_one_manual_feed_and_author(
    client: httpx.AsyncClient,
) -> None:
    headers = await _headers(client)

    responses = await asyncio.gather(
        *(
            client.post(
                "/articles/save-url", headers=headers, json={"url": f"https://example.com/{n}"}
            )
            for n in range(5)
        )
    )

    assert {response.status_code for response in responses} == {201}
    async with async_sessionmaker(get_engine())() as session:
        manual = await session.scalar(
            select(func.count()).select_from(Feed).where(Feed.source_type == SourceType.MANUAL)
        )
    assert manual == 1
    assert await _count(Author) == 1
    assert await _count(Article) == 5


async def test_concurrent_saves_of_the_same_url_create_one_article(
    client: httpx.AsyncClient,
) -> None:
    headers = await _headers(client)

    responses = await asyncio.gather(
        *(
            client.post(
                "/articles/save-url", headers=headers, json={"url": "https://example.com/same"}
            )
            for _ in range(5)
        )
    )

    assert {response.status_code for response in responses} == {201}
    assert await _count(Article) == 1


@pytest.mark.parametrize(
    "url",
    [
        "javascript:alert(1)",
        "file:///etc/passwd",
        "ftp://example.com/a",
        "not a url",
        "https:///no-host",
        "https://example.com/" + "a" * 2100,
    ],
)
async def test_save_url_rejects_non_http_or_oversized_urls(
    client: httpx.AsyncClient, url: str
) -> None:
    headers = await _headers(client)

    response = await client.post("/articles/save-url", headers=headers, json={"url": url})

    assert response.status_code == 422
