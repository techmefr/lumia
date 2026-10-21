from collections.abc import AsyncIterator
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import httpx
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from api.domain.article.models import Article, Author
from api.domain.feed.models import Feed, Folder, SourceType
from api.domain.fever.key_service import derive_api_key
from api.domain.user.models import Instance, Role, User
from api.main import app
from api.technical.auth.jwt import create_access_token
from config.database import get_engine

ADMIN_PAYLOAD = {
    "email": "admin@example.com",
    "username": "admin",
    "password": "correct-horse-battery-staple",
}


@dataclass
class Seeded:
    folder: int
    filed_feed: int
    loose_feed: int
    articles: list[int]


@pytest.fixture
async def client(db_schema: None) -> AsyncIterator[httpx.AsyncClient]:
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as async_client:
        yield async_client


def sessions() -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(get_engine(), expire_on_commit=False)


async def admin_headers(client: httpx.AsyncClient) -> dict[str, str]:
    response = await client.post("/onboarding/admin", json=ADMIN_PAYLOAD)
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


async def issue_api_key(client: httpx.AsyncClient, headers: dict[str, str]) -> str:
    created = (await client.post("/me/fever", headers=headers)).json()
    return derive_api_key(created["email"], created["secret"])


async def add_second_reader() -> dict[str, str]:
    async with sessions()() as session:
        instance = (await session.scalars(select(Instance))).one()
        second = User(
            instance_id=instance.id,
            email="second@example.com",
            username="second",
            role=Role.MEMBER,
        )
        session.add(second)
        await session.commit()
        return {"Authorization": f"Bearer {create_access_token(second.id)}"}


async def seed(owner_email: str = "admin@example.com", count: int = 3) -> Seeded:
    """One filed feed, one loose feed, and `count` articles spread over both, oldest first."""
    async with sessions()() as session:
        owner = (await session.scalars(select(User).where(User.email == owner_email))).one()
        folder = Folder(user_id=owner.id, name="Tech")
        session.add(folder)
        await session.flush()
        filed = Feed(
            user_id=owner.id,
            folder_id=folder.id,
            source_type=SourceType.MINIFLUX,
            external_feed_id=f"filed-{owner_email}",
            title="Filed feed",
            url="https://example.com/filed.xml",
        )
        loose = Feed(
            user_id=owner.id,
            source_type=SourceType.MINIFLUX,
            external_feed_id=f"loose-{owner_email}",
            title="Loose feed",
            url="https://example.com/loose.xml",
        )
        author = Author(name=f"Ada {owner_email}")
        session.add_all([filed, loose, author])
        await session.flush()
        articles = []
        for index in range(count):
            article = Article(
                feed_id=(filed if index % 2 == 0 else loose).id,
                author_id=author.id,
                external_entry_id=f"{owner_email}-{index}",
                title=f"Article {index}",
                url=f"https://example.com/{owner_email}/{index}",
                content=f"<p>Body {index}</p>",
                published_at=datetime(2026, 10, 1, 12, 0, tzinfo=UTC) + timedelta(days=index),
            )
            session.add(article)
            articles.append(article)
        await session.commit()
        return Seeded(
            folder=folder.fever_id,
            filed_feed=filed.fever_id,
            loose_feed=loose.fever_id,
            articles=[article.fever_id for article in articles],
        )
