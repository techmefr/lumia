from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from api.domain.article.models import Author, Category, Keyword, Lang
from api.domain.feed.models import Feed, SourceType
from api.domain.recommendation.models import (
    UserAuthorScore,
    UserCategoryScore,
    UserFeedScore,
    UserKeywordScore,
)
from api.domain.user.account_service import delete_account
from api.domain.user.exceptions import LastAdminError
from api.domain.user.models import Instance, MagicLinkToken, RefreshToken, Role, User
from config.database import get_engine


@pytest.fixture
async def session(db_schema: None) -> AsyncIterator[AsyncSession]:
    async with async_sessionmaker(get_engine(), expire_on_commit=False)() as async_session:
        yield async_session


async def _instance(session: AsyncSession) -> Instance:
    instance = Instance(max_accounts=5, disk_quota_mb=1024)
    session.add(instance)
    await session.flush()
    return instance


def _user(instance: Instance, email: str, role: Role = Role.MEMBER) -> User:
    return User(instance_id=instance.id, email=email, username=email.split("@", 1)[0], role=role)


async def _count(session: AsyncSession, model: type) -> int:
    return await session.scalar(select(func.count()).select_from(model)) or 0


async def test_the_learned_scores_go_with_the_account(session: AsyncSession) -> None:
    """They are keyed on the reader alone, so nothing else would ever collect them."""
    instance = await _instance(session)
    reader = _user(instance, "reader@example.com")
    session.add(reader)
    await session.flush()
    feed = Feed(
        user_id=reader.id,
        source_type=SourceType.MINIFLUX,
        external_feed_id="1",
        title="A blog",
        url="https://blog.test/rss",
    )
    keyword = Keyword(term="rss", lang=Lang.FR)
    author = Author(name="Someone")
    category = Category(name="Tech")
    session.add_all([feed, keyword, author, category])
    await session.flush()
    session.add_all(
        [
            UserFeedScore(user_id=reader.id, feed_id=feed.id, score=1.0),
            UserKeywordScore(user_id=reader.id, keyword_id=keyword.id, score=1.0),
            UserAuthorScore(user_id=reader.id, author_id=author.id, score=1.0),
            UserCategoryScore(user_id=reader.id, category_id=category.id, score=1.0),
        ]
    )
    await session.commit()

    await delete_account(session, reader.id)

    for score_model in (UserFeedScore, UserKeywordScore, UserAuthorScore, UserCategoryScore):
        assert await _count(session, score_model) == 0
    # The shared vocabulary is not the reader's to take away.
    for shared_model in (Keyword, Author, Category):
        assert await _count(session, shared_model) == 1


async def test_the_login_tokens_go_with_the_account(session: AsyncSession) -> None:
    instance = await _instance(session)
    reader = _user(instance, "reader@example.com")
    session.add(reader)
    await session.flush()
    expires_at = datetime.now(UTC) + timedelta(days=1)
    session.add_all(
        [
            RefreshToken(user_id=reader.id, token="a" * 64, expires_at=expires_at),
            MagicLinkToken(user_id=reader.id, token="b" * 64, expires_at=expires_at),
        ]
    )
    await session.commit()

    await delete_account(session, reader.id)

    assert await _count(session, RefreshToken) == 0
    assert await _count(session, MagicLinkToken) == 0
    assert await _count(session, User) == 0


async def test_deleting_an_unknown_account_is_a_no_op(session: AsyncSession) -> None:
    await _instance(session)
    await session.commit()

    await delete_account(session, uuid4())


async def test_the_only_admin_is_refused(session: AsyncSession) -> None:
    instance = await _instance(session)
    admin = _user(instance, "admin@example.com", Role.ADMIN)
    session.add_all([admin, _user(instance, "member@example.com")])
    await session.commit()

    with pytest.raises(LastAdminError):
        await delete_account(session, admin.id)

    assert await _count(session, User) == 2


async def test_an_admin_of_another_instance_does_not_count(session: AsyncSession) -> None:
    """Each instance is administered on its own; a neighbour's admin cannot stand in."""
    instance = await _instance(session)
    other = Instance(max_accounts=5, disk_quota_mb=1024)
    session.add(other)
    await session.flush()
    admin = _user(instance, "admin@example.com", Role.ADMIN)
    session.add_all([admin, _user(other, "elsewhere@example.com", Role.ADMIN)])
    await session.commit()

    with pytest.raises(LastAdminError):
        await delete_account(session, admin.id)
