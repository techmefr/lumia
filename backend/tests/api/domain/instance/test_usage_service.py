from datetime import UTC, datetime

import httpx
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.domain.article.models import Article
from api.domain.feed.models import Feed, SourceType
from api.domain.instance.exceptions import AccountQuotaExceededError
from api.domain.instance.usage_service import (
    BYTES_PER_MB,
    ensure_within_disk_quota,
    get_account_used_bytes,
    list_account_usages,
)
from api.domain.user.models import Instance, User
from api.main import app
from tests.api.domain.instance.conftest import add_member
from worker.technical.content_extraction import ExtractedPage, get_page_extractor

ONE_MEGABYTE_OF_TEXT = "x" * BYTES_PER_MB


class _FakePageExtractor:
    async def fetch(self, url: str) -> ExtractedPage:
        return ExtractedPage(
            title="Un titre",
            content="<p>Court.</p>",
            image_url=None,
            author=None,
            published_at=datetime(2026, 9, 1, tzinfo=UTC),
        )


async def _store_article(session: AsyncSession, user: User, content: str) -> None:
    feed = Feed(
        user_id=user.id,
        source_type=SourceType.MANUAL,
        external_feed_id="manual",
        title="Enregistrés",
        url="",
    )
    session.add(feed)
    await session.flush()
    session.add(
        Article(
            feed_id=feed.id,
            external_entry_id=f"https://example.com/{len(content)}",
            title="Un titre",
            url=f"https://example.com/{len(content)}",
            content=content,
            published_at=datetime(2026, 9, 1, tzinfo=UTC),
        )
    )
    await session.commit()


async def _current_admin(session: AsyncSession) -> User:
    admin = await session.scalar(select(User))
    assert admin is not None
    return admin


async def test_an_account_without_an_article_occupies_nothing(
    session: AsyncSession, admin_headers: dict[str, str]
) -> None:
    admin = await _current_admin(session)

    assert await get_account_used_bytes(session, admin.id) == 0


async def test_what_an_account_stores_is_the_text_of_its_own_articles(
    session: AsyncSession, admin_headers: dict[str, str]
) -> None:
    admin = await _current_admin(session)
    member = await add_member(session)
    await _store_article(session, admin, ONE_MEGABYTE_OF_TEXT)

    assert await get_account_used_bytes(session, admin.id) == BYTES_PER_MB
    assert await get_account_used_bytes(session, member.id) == 0

    usages = {usage.email: usage.used_mb for usage in await list_account_usages(session)}
    assert usages == {"admin@example.com": 1, "membre@example.com": 0}


async def test_the_quota_is_reached_when_the_stored_text_fills_it(
    session: AsyncSession, admin_headers: dict[str, str]
) -> None:
    admin = await _current_admin(session)
    instance = await session.scalar(select(Instance))
    assert instance is not None
    instance.disk_quota_mb = 1
    await session.commit()

    await ensure_within_disk_quota(session, instance, admin)

    await _store_article(session, admin, ONE_MEGABYTE_OF_TEXT)
    with pytest.raises(AccountQuotaExceededError):
        await ensure_within_disk_quota(session, instance, admin)


async def test_saving_a_url_is_refused_once_the_account_quota_is_full(
    client: httpx.AsyncClient, session: AsyncSession, admin_headers: dict[str, str]
) -> None:
    app.dependency_overrides[get_page_extractor] = lambda: _FakePageExtractor()
    try:
        first = await client.post(
            "/articles/save-url", headers=admin_headers, json={"url": "https://example.com/a"}
        )
        assert first.status_code == 201

        instance = await session.scalar(select(Instance))
        assert instance is not None
        instance.disk_quota_mb = 1
        await session.commit()
        admin = await _current_admin(session)
        await _store_article(session, admin, ONE_MEGABYTE_OF_TEXT)

        refused = await client.post(
            "/articles/save-url", headers=admin_headers, json={"url": "https://example.com/b"}
        )
    finally:
        app.dependency_overrides.clear()

    assert refused.status_code == 413
    assert "Mo" in refused.json()["detail"]
