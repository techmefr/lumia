from collections.abc import AsyncIterator
from datetime import UTC, datetime
from uuid import UUID

import httpx
import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from api.domain.article.models import Article
from api.domain.export import export_service
from api.domain.export.models import ExportJob
from api.domain.export.routes import get_export_queue
from api.domain.feed.models import Feed, SourceType
from api.domain.playlist.models import MemberRole, Playlist, PlaylistItem, PlaylistMember
from api.domain.user.models import User
from api.main import app
from api.technical.auth.jwt import create_access_token
from config.database import get_engine

ADMIN_PAYLOAD = {
    "email": "admin@example.com",
    "username": "admin",
    "password": "correct-horse-battery-staple",
}


class RecordingQueue:
    def __init__(self) -> None:
        self.enqueued: list[UUID] = []

    async def enqueue_playlist_epub(self, job_id: UUID) -> None:
        self.enqueued.append(job_id)


@pytest.fixture
async def client(db_schema: None) -> AsyncIterator[httpx.AsyncClient]:
    queue = RecordingQueue()
    app.dependency_overrides[get_export_queue] = lambda: queue
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as async_client:
        yield async_client
    app.dependency_overrides.pop(get_export_queue, None)


@pytest.fixture
async def session(db_schema: None) -> AsyncIterator[AsyncSession]:
    async with async_sessionmaker(get_engine(), expire_on_commit=False)() as db_session:
        yield db_session


async def _seed_shared_playlist(
    client: httpx.AsyncClient, session: AsyncSession
) -> tuple[Playlist, User]:
    await client.post("/onboarding/admin", json=ADMIN_PAYLOAD)
    owner = (await session.scalars(select(User))).one()
    member = User(instance_id=owner.instance_id, email="member@example.com", username="member")
    session.add(member)
    await session.flush()
    feed = Feed(
        user_id=owner.id,
        source_type=SourceType.MINIFLUX,
        external_feed_id="1",
        title="Feed",
        url="https://example.com/feed",
    )
    session.add(feed)
    await session.flush()
    playlist = Playlist(user_id=owner.id, name="Shared")
    session.add(playlist)
    await session.flush()
    article = Article(
        feed_id=feed.id,
        external_entry_id="e",
        title="Article",
        url="https://example.com/a",
        content="<p>Body</p>",
        published_at=datetime(2026, 8, 12, tzinfo=UTC),
    )
    session.add(article)
    await session.flush()
    session.add(PlaylistItem(playlist_id=playlist.id, article_id=article.id, position=0))
    session.add(PlaylistMember(playlist_id=playlist.id, user_id=member.id, role=MemberRole.VIEWER))
    await session.commit()
    return playlist, member


async def test_a_member_exporting_a_shared_playlist_owns_the_resulting_job(
    client: httpx.AsyncClient, session: AsyncSession
) -> None:
    playlist, member = await _seed_shared_playlist(client, session)
    headers = {"Authorization": f"Bearer {create_access_token(member.id)}"}

    response = await client.post(f"/playlists/{playlist.id}/export-epub", headers=headers)

    assert response.status_code == 202
    job = await session.get(ExportJob, UUID(response.json()["id"]))
    assert job is not None
    assert job.user_id == member.id
    assert (await client.get(f"/exports/{job.id}", headers=headers)).status_code == 200


async def test_the_owner_does_not_see_the_job_a_member_asked_for(
    client: httpx.AsyncClient, session: AsyncSession
) -> None:
    playlist, member = await _seed_shared_playlist(client, session)
    member_headers = {"Authorization": f"Bearer {create_access_token(member.id)}"}
    owner = (await session.scalars(select(User).where(User.username == "admin"))).one()
    owner_headers = {"Authorization": f"Bearer {create_access_token(owner.id)}"}
    created = await client.post(f"/playlists/{playlist.id}/export-epub", headers=member_headers)

    response = await client.get(f"/exports/{created.json()['id']}", headers=owner_headers)

    assert response.status_code == 404


async def test_a_reader_cannot_pile_up_more_live_exports_than_the_quota(
    client: httpx.AsyncClient, session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    playlist, member = await _seed_shared_playlist(client, session)
    headers = {"Authorization": f"Bearer {create_access_token(member.id)}"}
    monkeypatch.setattr(export_service, "MAX_LIVE_EXPORTS_PER_USER", 1)
    other = Playlist(user_id=member.id, name="Second")
    session.add(other)
    await session.flush()
    article = (await session.scalars(select(Article))).one()
    session.add(PlaylistItem(playlist_id=other.id, article_id=article.id, position=0))
    await session.commit()

    first = await client.post(f"/playlists/{playlist.id}/export-epub", headers=headers)
    second = await client.post(f"/playlists/{other.id}/export-epub", headers=headers)

    assert first.status_code == 202
    assert second.status_code == 429
    assert second.json()["detail"] == "export_quota_exceeded"
    jobs = await session.scalar(select(func.count()).select_from(ExportJob))
    assert jobs == 1
