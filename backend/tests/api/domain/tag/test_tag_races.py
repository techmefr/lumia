from collections.abc import AsyncIterator
from datetime import UTC, datetime
from uuid import UUID

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from api.domain.article.models import Article
from api.domain.feed.models import Feed, SourceType
from api.domain.tag import service
from api.domain.tag.exceptions import TagNameTakenError
from api.domain.tag.models import ArticleTag, Tag
from api.domain.user.models import Instance, User
from config.database import get_engine


@pytest.fixture
async def session(db_schema: None) -> AsyncIterator[AsyncSession]:
    async with async_sessionmaker(get_engine(), expire_on_commit=False)() as db_session:
        yield db_session


async def _seed(session: AsyncSession) -> tuple[UUID, UUID]:
    instance = Instance(max_accounts=10, disk_quota_mb=1000)
    session.add(instance)
    await session.flush()
    user = User(instance_id=instance.id, email="a@example.com", username="a")
    session.add(user)
    await session.flush()
    feed = Feed(
        user_id=user.id,
        source_type=SourceType.MINIFLUX,
        external_feed_id="1",
        title="Feed",
        url="https://example.com/feed",
    )
    session.add(feed)
    await session.flush()
    article = Article(
        feed_id=feed.id,
        external_entry_id="1",
        title="T",
        url="https://example.com/a",
        content="c",
        published_at=datetime(2026, 10, 1, tzinfo=UTC),
    )
    session.add(article)
    await session.commit()
    return user.id, article.id


async def test_attaching_a_tag_created_concurrently_reuses_it(
    session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    user_id, article_id = await _seed(session)
    await service.create_tag(session, user_id, "Python")
    real = service._find_by_name
    calls = {"count": 0}

    async def find(session: AsyncSession, user_id: UUID, name: str) -> Tag | None:
        calls["count"] += 1
        if calls["count"] == 1:
            return None
        return await real(session, user_id, name)

    monkeypatch.setattr(service, "_find_by_name", find)

    tags = await service.attach_by_name(session, user_id, article_id, "python")

    assert [tag.name for tag in tags] == ["Python"]
    assert await session.scalar(select(func.count()).select_from(Tag)) == 1
    assert await session.scalar(select(func.count()).select_from(ArticleTag)) == 1


async def test_renaming_onto_a_name_taken_concurrently_raises_name_taken(
    session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    user_id, _article_id = await _seed(session)
    await service.create_tag(session, user_id, "Python")
    other = await service.create_tag(session, user_id, "Rust")

    async def blind(session: AsyncSession, user_id: UUID, name: str) -> Tag | None:
        return None

    monkeypatch.setattr(service, "_find_by_name", blind)

    with pytest.raises(TagNameTakenError):
        await service.rename_tag(session, user_id, other.id, "python")

    names = sorted(await session.scalars(select(Tag.name)))
    assert names == ["Python", "Rust"]
