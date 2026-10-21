from datetime import UTC, datetime, timedelta
from typing import Protocol
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.domain.export.models import ExportJob, ExportKind, ExportStatus
from api.domain.playlist.models import Playlist

MAX_PLAYLIST_ARTICLES = 200
EXPORT_LIFETIME = timedelta(hours=24)


class EmptyPlaylistError(Exception):
    pass


class PlaylistTooLargeError(Exception):
    pass


class ExportNotFoundError(Exception):
    pass


class ExportNotReadyError(Exception):
    pass


class ExportQueue(Protocol):
    async def enqueue_playlist_epub(self, job_id: UUID) -> None: ...


async def request_playlist_epub(
    session: AsyncSession, queue: ExportQueue, playlist: Playlist
) -> ExportJob:
    """Starts the build of a playlist's book, or hands back the one already under way.

    A second click while the first book is still being built would only make the worker do the
    same work twice, so a pending job for the same playlist is returned as it is.
    """
    if not playlist.items:
        raise EmptyPlaylistError
    if len(playlist.items) > MAX_PLAYLIST_ARTICLES:
        raise PlaylistTooLargeError

    pending = await session.scalar(
        select(ExportJob).where(
            ExportJob.user_id == playlist.user_id,
            ExportJob.kind == ExportKind.PLAYLIST_EPUB,
            ExportJob.subject_id == playlist.id,
            ExportJob.status == ExportStatus.PENDING,
            ExportJob.expires_at > datetime.now(UTC),
        )
    )
    if pending is not None:
        return pending

    job = ExportJob(
        user_id=playlist.user_id,
        kind=ExportKind.PLAYLIST_EPUB,
        subject_id=playlist.id,
        expires_at=datetime.now(UTC) + EXPORT_LIFETIME,
    )
    session.add(job)
    await session.commit()
    await queue.enqueue_playlist_epub(job.id)
    return job


async def get_own_job(session: AsyncSession, user_id: UUID, job_id: UUID) -> ExportJob:
    job = await session.scalar(
        select(ExportJob).where(
            ExportJob.id == job_id,
            ExportJob.user_id == user_id,
            ExportJob.expires_at > datetime.now(UTC),
        )
    )
    if job is None:
        raise ExportNotFoundError
    return job


async def get_file(session: AsyncSession, user_id: UUID, job_id: UUID) -> tuple[str, bytes]:
    job = await get_own_job(session, user_id, job_id)
    if job.status is not ExportStatus.READY:
        raise ExportNotReadyError
    await session.refresh(job, ["data"])
    if job.data is None or job.file_name is None:
        raise ExportNotReadyError
    return job.file_name, job.data
