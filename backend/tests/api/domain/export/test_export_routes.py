from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import httpx
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker

from api.domain.article.models import Article
from api.domain.export import export_service
from api.domain.export.models import ExportJob, ExportKind, ExportStatus
from api.domain.export.routes import get_export_queue
from api.domain.feed.models import Feed, SourceType
from api.domain.playlist.models import Playlist, PlaylistItem
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
def queue() -> RecordingQueue:
    return RecordingQueue()


@pytest.fixture
async def client(db_schema: None, queue: RecordingQueue) -> AsyncIterator[httpx.AsyncClient]:
    app.dependency_overrides[get_export_queue] = lambda: queue
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as async_client:
        yield async_client
    app.dependency_overrides.pop(get_export_queue, None)


async def _headers(client: httpx.AsyncClient) -> dict[str, str]:
    response = await client.post("/onboarding/admin", json=ADMIN_PAYLOAD)
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


async def _seed_playlist(*, articles: int = 2) -> UUID:
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
        session.add(feed)
        await session.flush()
        playlist = Playlist(user_id=user.id, name="Lectures du soir")
        session.add(playlist)
        await session.flush()
        for position in range(articles):
            article = Article(
                feed_id=feed.id,
                external_entry_id=f"e{position}",
                title=f"Article {position}",
                url=f"https://example.com/{position}",
                content="<p>Corps</p>",
                published_at=datetime(2026, 8, 12, tzinfo=UTC),
            )
            session.add(article)
            await session.flush()
            session.add(
                PlaylistItem(playlist_id=playlist.id, article_id=article.id, position=position)
            )
        await session.commit()
        return playlist.id


async def _seed_job(
    *,
    status: ExportStatus = ExportStatus.READY,
    data: bytes | None = b"epub-bytes",
    expires_in: timedelta = timedelta(hours=1),
    owner_email: str | None = None,
) -> UUID:
    session_factory = async_sessionmaker(get_engine(), expire_on_commit=False)
    async with session_factory() as session:
        user = (await session.scalars(select(User))).first()
        assert user is not None
        user_id = user.id
        if owner_email is not None:
            other = User(
                instance_id=user.instance_id,
                email=owner_email,
                username="other",
                password_hash=None,
            )
            session.add(other)
            await session.flush()
            user_id = other.id
        job = ExportJob(
            user_id=user_id,
            kind=ExportKind.PLAYLIST_EPUB,
            subject_id=uuid4(),
            status=status,
            file_name="Lectures du soir.epub",
            data=data,
            expires_at=datetime.now(UTC) + expires_in,
        )
        session.add(job)
        await session.commit()
        return job.id


async def test_asking_for_a_playlist_book_queues_a_job_and_answers_immediately(
    client: httpx.AsyncClient, queue: RecordingQueue
) -> None:
    headers = await _headers(client)
    playlist_id = await _seed_playlist()

    response = await client.post(f"/playlists/{playlist_id}/export-epub", headers=headers)

    assert response.status_code == 202
    body = response.json()
    assert body["status"] == "pending"
    assert body["kind"] == "playlist_epub"
    assert queue.enqueued == [UUID(body["id"])]


async def test_a_second_request_while_the_first_is_pending_reuses_it(
    client: httpx.AsyncClient, queue: RecordingQueue
) -> None:
    headers = await _headers(client)
    playlist_id = await _seed_playlist()

    first = await client.post(f"/playlists/{playlist_id}/export-epub", headers=headers)
    second = await client.post(f"/playlists/{playlist_id}/export-epub", headers=headers)

    assert second.json()["id"] == first.json()["id"]
    assert len(queue.enqueued) == 1


async def test_an_empty_playlist_has_nothing_to_export(
    client: httpx.AsyncClient, queue: RecordingQueue
) -> None:
    headers = await _headers(client)
    playlist_id = await _seed_playlist(articles=0)

    response = await client.post(f"/playlists/{playlist_id}/export-epub", headers=headers)

    assert response.status_code == 422
    assert response.json()["detail"] == "empty_playlist"
    assert queue.enqueued == []


async def test_a_playlist_over_the_cap_is_refused(
    client: httpx.AsyncClient, queue: RecordingQueue, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(export_service, "MAX_PLAYLIST_ARTICLES", 1)
    headers = await _headers(client)
    playlist_id = await _seed_playlist(articles=2)

    response = await client.post(f"/playlists/{playlist_id}/export-epub", headers=headers)

    assert response.status_code == 413
    assert response.json()["detail"] == "playlist_too_large"
    assert queue.enqueued == []


async def test_a_playlist_of_another_reader_cannot_be_exported(
    client: httpx.AsyncClient, queue: RecordingQueue
) -> None:
    await _headers(client)
    playlist_id = await _seed_playlist()
    session_factory = async_sessionmaker(get_engine(), expire_on_commit=False)
    async with session_factory() as session:
        admin = (await session.scalars(select(User))).one()
        other = User(
            instance_id=admin.instance_id,
            email="other@example.com",
            username="other",
            password_hash=None,
        )
        session.add(other)
        await session.commit()
        other_id = other.id

    response = await client.post(
        f"/playlists/{playlist_id}/export-epub",
        headers={"Authorization": f"Bearer {create_access_token(other_id)}"},
    )

    assert response.status_code == 404
    assert queue.enqueued == []


async def test_the_status_of_a_job_is_readable_by_its_owner(client: httpx.AsyncClient) -> None:
    headers = await _headers(client)
    job_id = await _seed_job(status=ExportStatus.PENDING, data=None)

    response = await client.get(f"/exports/{job_id}", headers=headers)

    assert response.status_code == 200
    assert response.json()["status"] == "pending"


async def test_a_job_of_another_reader_is_a_404(client: httpx.AsyncClient) -> None:
    headers = await _headers(client)
    job_id = await _seed_job(owner_email="other@example.com")

    assert (await client.get(f"/exports/{job_id}", headers=headers)).status_code == 404
    assert (await client.get(f"/exports/{job_id}/download", headers=headers)).status_code == 404


async def test_an_expired_job_is_gone(client: httpx.AsyncClient) -> None:
    headers = await _headers(client)
    job_id = await _seed_job(expires_in=timedelta(minutes=-1))

    assert (await client.get(f"/exports/{job_id}", headers=headers)).status_code == 404
    assert (await client.get(f"/exports/{job_id}/download", headers=headers)).status_code == 404


async def test_the_file_is_downloaded_once_it_is_ready(client: httpx.AsyncClient) -> None:
    headers = await _headers(client)
    job_id = await _seed_job()

    response = await client.get(f"/exports/{job_id}/download", headers=headers)

    assert response.status_code == 200
    assert response.content == b"epub-bytes"
    assert response.headers["content-type"] == "application/epub+zip"
    assert 'filename="Lectures-du-soir.epub"' in response.headers["content-disposition"]


@pytest.mark.parametrize("status", [ExportStatus.PENDING, ExportStatus.FAILED])
async def test_the_file_is_not_downloadable_before_it_is_ready(
    client: httpx.AsyncClient, status: ExportStatus
) -> None:
    headers = await _headers(client)
    job_id = await _seed_job(status=status, data=None)

    response = await client.get(f"/exports/{job_id}/download", headers=headers)

    assert response.status_code == 409
    assert response.json()["detail"] == "export_not_ready"


async def test_the_export_routes_require_a_session(client: httpx.AsyncClient) -> None:
    assert (await client.post(f"/playlists/{uuid4()}/export-epub")).status_code == 401
    assert (await client.get(f"/exports/{uuid4()}")).status_code == 401
    assert (await client.get(f"/exports/{uuid4()}/download")).status_code == 401
