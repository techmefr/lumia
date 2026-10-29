from collections.abc import AsyncIterator
from datetime import UTC, datetime
from uuid import UUID

import httpx
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from api.domain.article.models import Article
from api.domain.feed.models import Feed, SourceType
from api.domain.recommendation.models import UserArticleFeedback
from api.domain.user.models import Instance, User
from api.domain.webhook.models import OutboundWebhook, WebhookDelivery, WebhookEvent
from api.domain.webhook.publisher import EventPublisher
from api.main import app
from api.technical.auth.jwt import create_access_token
from config.database import get_engine

ADMIN_PAYLOAD = {
    "email": "admin@example.com",
    "username": "admin",
    "password": "correct-horse-battery-staple",
}


@pytest.fixture
async def client(db_schema: None) -> AsyncIterator[httpx.AsyncClient]:
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as async_client:
        yield async_client


@pytest.fixture
async def session(db_schema: None) -> AsyncIterator[AsyncSession]:
    session_factory = async_sessionmaker(get_engine(), expire_on_commit=False)
    async with session_factory() as db_session:
        yield db_session


async def _onboard(client: httpx.AsyncClient) -> None:
    await client.post("/onboarding/admin", json=ADMIN_PAYLOAD)


async def _article_of(session: AsyncSession, user: User, external_id: str) -> Article:
    feed = Feed(
        user_id=user.id,
        source_type=SourceType.MINIFLUX,
        external_feed_id=external_id,
        title="Feed",
        url=f"https://example.com/{external_id}",
    )
    session.add(feed)
    await session.flush()
    article = Article(
        feed_id=feed.id,
        external_entry_id=external_id,
        title="Title",
        url=f"https://example.com/{external_id}/a",
        content="Content",
        published_at=datetime(2026, 8, 12, tzinfo=UTC),
    )
    session.add(article)
    await session.commit()
    return article


async def _stranger(session: AsyncSession) -> User:
    instance = (await session.scalars(select(Instance))).one()
    user = User(instance_id=instance.id, email="stranger@example.com", username="stranger")
    session.add(user)
    await session.commit()
    return user


async def test_feedback_on_an_article_of_another_reader_is_a_404(
    client: httpx.AsyncClient, session: AsyncSession
) -> None:
    await _onboard(client)
    admin = (await session.scalars(select(User).where(User.username == "admin"))).one()
    stranger = await _stranger(session)
    foreign_article = await _article_of(session, stranger, "99")
    headers = {"Authorization": f"Bearer {create_access_token(admin.id)}"}

    response = await client.post(
        f"/articles/{foreign_article.id}/feedback", headers=headers, json={"saved": True}
    )

    assert response.status_code == 404
    assert (await session.scalars(select(UserArticleFeedback))).all() == []


async def test_feedback_on_an_own_article_is_still_accepted(
    client: httpx.AsyncClient, session: AsyncSession
) -> None:
    await _onboard(client)
    admin = (await session.scalars(select(User).where(User.username == "admin"))).one()
    article = await _article_of(session, admin, "10")
    headers = {"Authorization": f"Bearer {create_access_token(admin.id)}"}

    response = await client.post(
        f"/articles/{article.id}/feedback", headers=headers, json={"saved": True}
    )

    assert response.status_code == 204


class _RecordingPool:
    def __init__(self) -> None:
        self.jobs: list[str] = []

    async def enqueue_job(self, name: str, delivery_id: str) -> None:
        self.jobs.append(delivery_id)


async def _pool() -> _RecordingPool:
    return _RecordingPool()


async def _webhook_of(session: AsyncSession, user: User) -> OutboundWebhook:
    webhook = OutboundWebhook(
        user_id=user.id,
        url="https://hooks.example.com/in",
        secret_encrypted="x",
        events=[WebhookEvent.ARTICLE_SAVED.value],
    )
    session.add(webhook)
    await session.commit()
    return webhook


async def test_a_webhook_never_receives_the_article_of_another_reader(
    client: httpx.AsyncClient, session: AsyncSession
) -> None:
    await _onboard(client)
    admin = (await session.scalars(select(User).where(User.username == "admin"))).one()
    stranger = await _stranger(session)
    own = await _article_of(session, admin, "10")
    foreign = await _article_of(session, stranger, "99")
    await _webhook_of(session, admin)

    await EventPublisher(_pool).publish(
        session, admin.id, WebhookEvent.ARTICLE_SAVED, [own.id, foreign.id]
    )

    deliveries = (await session.scalars(select(WebhookDelivery))).all()
    article_ids = {UUID(str(delivery.payload["article"]["id"])) for delivery in deliveries}  # type: ignore[index]
    assert article_ids == {own.id}
