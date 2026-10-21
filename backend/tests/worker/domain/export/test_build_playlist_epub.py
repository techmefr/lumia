import io
import zipfile
from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from api.domain.article.models import Article, Author, Lang
from api.domain.export.models import ExportJob, ExportKind, ExportStatus
from api.domain.feed.models import Feed, SourceType
from api.domain.playlist.models import Playlist, PlaylistItem
from api.domain.user.models import Instance, User
from api.technical.net.image_fetcher import FetchedImage
from config.database import get_engine
from worker.domain.export.build_playlist_epub import build_playlist_epub
from worker.domain.maintenance.purge_exports import purge_expired_exports

PNG = FetchedImage(media_type="image/png", data=b"png-bytes")


class StubImages:
    async def fetch(self, url: str) -> FetchedImage | None:
        return PNG if url == "https://example.com/pic.png" else None


@pytest.fixture
async def session(db_schema: None) -> AsyncIterator[AsyncSession]:
    session_factory = async_sessionmaker(get_engine(), expire_on_commit=False)
    async with session_factory() as db_session:
        yield db_session


async def _seed_user(session: AsyncSession) -> User:
    instance = Instance(max_accounts=10, disk_quota_mb=1000)
    session.add(instance)
    await session.flush()
    user = User(instance_id=instance.id, email=f"{uuid4()}@example.com", username="reader")
    session.add(user)
    await session.flush()
    return user


async def _seed_playlist(session: AsyncSession, user: User, *, languages: list[Lang]) -> Playlist:
    feed = Feed(
        user_id=user.id,
        source_type=SourceType.MINIFLUX,
        external_feed_id=str(uuid4()),
        title="Seeded",
        url="https://example.com/feed",
    )
    author = Author(name=f"Ada {uuid4()}")
    session.add_all([feed, author])
    await session.flush()
    playlist = Playlist(user_id=user.id, name="Lectures du soir")
    session.add(playlist)
    await session.flush()
    for position, language in enumerate(languages):
        article = Article(
            feed_id=feed.id,
            author_id=author.id,
            external_entry_id=f"e{position}",
            title=f"Article {position}",
            url=f"https://example.com/{position}",
            content="<p>Corps</p><img src='/pic.png' alt=''>",
            original_lang=language,
            published_at=datetime(2026, 8, 12, tzinfo=UTC),
        )
        session.add(article)
        await session.flush()
        session.add(PlaylistItem(playlist_id=playlist.id, article_id=article.id, position=position))
    await session.commit()
    return playlist


async def _job(
    session: AsyncSession,
    user: User,
    playlist_id: UUID,
    *,
    status: ExportStatus = ExportStatus.PENDING,
) -> ExportJob:
    job = ExportJob(
        user_id=user.id,
        kind=ExportKind.PLAYLIST_EPUB,
        subject_id=playlist_id,
        status=status,
        expires_at=datetime.now(UTC) + timedelta(hours=1),
    )
    session.add(job)
    await session.commit()
    return job


async def test_the_playlist_becomes_a_book_with_one_chapter_per_article_in_order(
    session: AsyncSession,
) -> None:
    user = await _seed_user(session)
    playlist = await _seed_playlist(session, user, languages=[Lang.FR, Lang.FR, Lang.EN])
    job = await _job(session, user, playlist.id)

    await build_playlist_epub({}, str(job.id), images=StubImages())

    stored = await session.scalar(select(ExportJob).where(ExportJob.id == job.id))
    assert stored is not None
    await session.refresh(stored, ["data", "status", "file_name"])
    assert stored.status is ExportStatus.READY
    assert stored.file_name == "Lectures du soir.epub"
    assert stored.data is not None
    book = zipfile.ZipFile(io.BytesIO(stored.data))
    navigation = book.read("OEBPS/nav.xhtml").decode()
    assert (
        navigation.index("Article 0")
        < navigation.index("Article 1")
        < navigation.index("Article 2")
    )
    assert book.read("OEBPS/images/image-1.png") == PNG.data
    package = book.read("OEBPS/content.opf").decode()
    assert "<dc:language>fr</dc:language>" in package
    assert "<dc:title>Lectures du soir</dc:title>" in package


async def test_a_missing_playlist_marks_the_job_failed_instead_of_raising(
    session: AsyncSession,
) -> None:
    user = await _seed_user(session)
    job = await _job(session, user, uuid4())

    await build_playlist_epub({}, str(job.id), images=StubImages())

    await session.refresh(job)
    assert job.status is ExportStatus.FAILED


async def test_a_playlist_of_another_reader_is_not_built(session: AsyncSession) -> None:
    owner = await _seed_user(session)
    intruder = await _seed_user(session)
    playlist = await _seed_playlist(session, owner, languages=[Lang.FR])
    job = await _job(session, intruder, playlist.id)

    await build_playlist_epub({}, str(job.id), images=StubImages())

    await session.refresh(job)
    assert job.status is ExportStatus.FAILED


async def test_a_job_already_done_is_left_alone(session: AsyncSession) -> None:
    user = await _seed_user(session)
    playlist = await _seed_playlist(session, user, languages=[Lang.FR])
    job = await _job(session, user, playlist.id, status=ExportStatus.READY)

    await build_playlist_epub({}, str(job.id), images=StubImages())

    await session.refresh(job, ["status", "file_name"])
    assert job.status is ExportStatus.READY
    assert job.file_name is None


async def test_an_unknown_job_is_ignored(session: AsyncSession) -> None:
    await build_playlist_epub({}, str(uuid4()), images=StubImages())


async def test_expired_exports_are_purged_and_live_ones_kept(session: AsyncSession) -> None:
    user = await _seed_user(session)
    expired = await _job(session, user, uuid4())
    expired.expires_at = datetime.now(UTC) - timedelta(minutes=1)
    live = await _job(session, user, uuid4())
    await session.commit()

    purged = await purge_expired_exports({})

    assert purged == 1
    remaining = list(await session.scalars(select(ExportJob.id)))
    assert remaining == [live.id]
