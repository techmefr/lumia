import io
import zipfile
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from uuid import uuid4

import httpx
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker

from api.domain.article.models import Article, Author
from api.domain.feed.models import Feed, SourceType
from api.domain.user.models import User
from api.main import app
from api.technical.auth.jwt import create_access_token
from api.technical.net.image_fetcher import FetchedImage, get_image_fetcher
from config.database import get_engine

ADMIN_PAYLOAD = {
    "email": "admin@example.com",
    "username": "admin",
    "password": "correct-horse-battery-staple",
}


class StubImages:
    async def fetch(self, url: str) -> FetchedImage | None:
        if url == "https://example.com/pic.png":
            return FetchedImage(media_type="image/png", data=b"png-bytes")
        return None


@pytest.fixture
async def client(db_schema: None) -> AsyncIterator[httpx.AsyncClient]:
    app.dependency_overrides[get_image_fetcher] = StubImages
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as async_client:
        yield async_client
    app.dependency_overrides.pop(get_image_fetcher, None)


async def _headers(client: httpx.AsyncClient) -> dict[str, str]:
    response = await client.post("/onboarding/admin", json=ADMIN_PAYLOAD)
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


async def _seed_article(*, title: str = "Un été à Paris") -> str:
    session_factory = async_sessionmaker(get_engine(), expire_on_commit=False)
    async with session_factory() as session:
        user = (await session.scalars(select(User))).one()
        feed = Feed(
            user_id=user.id,
            source_type=SourceType.MINIFLUX,
            external_feed_id="seeded",
            title="Seeded",
            url="https://example.com/feed",
        )
        author = Author(name="Ada Lovelace")
        session.add_all([feed, author])
        await session.flush()
        article = Article(
            feed_id=feed.id,
            author_id=author.id,
            external_entry_id="e1",
            title=title,
            url="https://example.com/a",
            content="<p>Corps</p><img src='/pic.png' alt='photo'>",
            published_at=datetime(2026, 8, 12, tzinfo=UTC),
        )
        session.add(article)
        await session.commit()
        return str(article.id)


async def test_an_article_is_exported_as_an_epub_with_its_picture(
    client: httpx.AsyncClient,
) -> None:
    headers = await _headers(client)
    article_id = await _seed_article()

    response = await client.get(f"/articles/{article_id}/export.epub", headers=headers)

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/epub+zip"
    book = zipfile.ZipFile(io.BytesIO(response.content))
    assert book.read("OEBPS/images/image-1.png") == b"png-bytes"
    assert "Corps" in book.read("OEBPS/chapter-1.xhtml").decode()
    assert "<dc:creator>Ada Lovelace</dc:creator>" in book.read("OEBPS/content.opf").decode()


async def test_the_download_name_keeps_the_title_readable(client: httpx.AsyncClient) -> None:
    headers = await _headers(client)
    article_id = await _seed_article(title='Un "été" à Paris')

    response = await client.get(f"/articles/{article_id}/export.epub", headers=headers)

    disposition = response.headers["content-disposition"]
    assert disposition.startswith('attachment; filename="Un-ete-a-Paris.epub"')
    assert "filename*=UTF-8''" in disposition
    assert "%C3%A9t%C3%A9" in disposition


async def test_an_article_of_another_reader_is_not_exportable(client: httpx.AsyncClient) -> None:
    await _headers(client)
    article_id = await _seed_article()
    session_factory = async_sessionmaker(get_engine(), expire_on_commit=False)
    async with session_factory() as session:
        user = (await session.scalars(select(User))).one()
        other = User(
            instance_id=user.instance_id,
            email="other@example.com",
            username="other",
            password_hash=None,
        )
        session.add(other)
        await session.commit()
        other_id = other.id

    response = await client.get(
        f"/articles/{article_id}/export.epub",
        headers={"Authorization": f"Bearer {create_access_token(other_id)}"},
    )

    assert response.status_code == 404


async def test_an_unknown_article_is_a_404(client: httpx.AsyncClient) -> None:
    headers = await _headers(client)

    response = await client.get(f"/articles/{uuid4()}/export.epub", headers=headers)

    assert response.status_code == 404


async def test_the_export_requires_a_session(client: httpx.AsyncClient) -> None:
    response = await client.get(f"/articles/{uuid4()}/export.epub")

    assert response.status_code == 401
