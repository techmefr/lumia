from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from api.domain.article.export_filename import attachment_header
from api.domain.export.export_service import (
    EmptyPlaylistError,
    ExportNotFoundError,
    ExportNotReadyError,
    ExportQueue,
    PlaylistTooLargeError,
    get_file,
    get_own_job,
    request_playlist_epub,
)
from api.domain.export.models import ExportJob
from api.domain.export.schemas import ExportJobResponse
from api.domain.playlist.exceptions import PlaylistNotFoundError
from api.domain.playlist.playlist_service import get_playlist
from api.domain.user.dependencies import get_current_user
from api.domain.user.models import User
from api.technical.db import get_db_session
from worker.technical.queue import get_arq_pool

router = APIRouter()


class ArqExportQueue:
    async def enqueue_playlist_epub(self, job_id: UUID) -> None:
        pool = await get_arq_pool()
        await pool.enqueue_job("build_playlist_epub", str(job_id))


def get_export_queue() -> ExportQueue:
    return ArqExportQueue()


def _to_response(job: ExportJob) -> ExportJobResponse:
    return ExportJobResponse(id=job.id, kind=job.kind, status=job.status, file_name=job.file_name)


@router.post(
    "/playlists/{playlist_id}/export-epub",
    response_model=ExportJobResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def export_playlist_epub(
    playlist_id: UUID,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
    queue: ExportQueue = Depends(get_export_queue),
) -> ExportJobResponse:
    try:
        playlist = await get_playlist(session, user.id, playlist_id)
    except PlaylistNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND) from exc
    try:
        job = await request_playlist_epub(session, queue, playlist)
    except EmptyPlaylistError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="empty_playlist"
        ) from exc
    except PlaylistTooLargeError as exc:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE, detail="playlist_too_large"
        ) from exc
    return _to_response(job)


@router.get("/exports/{job_id}", response_model=ExportJobResponse)
async def get_export(
    job_id: UUID,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> ExportJobResponse:
    try:
        return _to_response(await get_own_job(session, user.id, job_id))
    except ExportNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND) from exc


@router.get("/exports/{job_id}/download")
async def download_export(
    job_id: UUID,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> Response:
    try:
        file_name, data = await get_file(session, user.id, job_id)
    except ExportNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND) from exc
    except ExportNotReadyError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="export_not_ready"
        ) from exc
    stem, _, extension = file_name.rpartition(".")
    return Response(
        content=data,
        media_type="application/epub+zip",
        headers={"Content-Disposition": attachment_header(stem, extension)},
    )
