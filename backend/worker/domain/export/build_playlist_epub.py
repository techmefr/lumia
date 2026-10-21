import logging
from collections import Counter
from typing import Any
from uuid import UUID

from sqlalchemy import select

from api.domain.article.epub_export import EpubChapter, build_epub
from api.domain.article.export_filename import file_stem
from api.domain.article.models import Article
from api.domain.export.models import ExportJob, ExportStatus
from api.domain.playlist.models import Playlist
from api.technical.net.image_fetcher import GuardedImageFetcher, ImageFetcher
from worker.technical.db import worker_session

logger = logging.getLogger(__name__)

_FALLBACK_LANGUAGE = "en"


async def build_playlist_epub(
    ctx: dict[Any, Any], job_id: str, *, images: ImageFetcher | None = None
) -> None:
    """Builds the book of a playlist and parks it on the job until the reader downloads it.

    A failure is recorded on the job instead of being raised: the reader is polling that row, and
    a job that died with an exception would leave it pending until it expired.
    """
    async with worker_session() as session:
        job = await session.get(ExportJob, UUID(job_id))
        if job is None or job.status is not ExportStatus.PENDING:
            return
        try:
            playlist = await session.scalar(
                select(Playlist).where(
                    Playlist.id == job.subject_id, Playlist.user_id == job.user_id
                )
            )
            if playlist is None or not playlist.items:
                raise LookupError("playlist is gone or empty")
            articles = [item.article for item in playlist.items]
            job.data = await build_epub(
                title=playlist.name,
                language=_dominant_language(articles),
                chapters=[_chapter(article) for article in articles],
                images=images or GuardedImageFetcher(),
            )
            job.file_name = f"{file_stem(playlist.name)}.epub"
            job.status = ExportStatus.READY
        except Exception:
            logger.exception("playlist epub %s failed", job_id)
            job.status = ExportStatus.FAILED
        await session.commit()


def _chapter(article: Article) -> EpubChapter:
    return EpubChapter(
        title=article.title,
        author=article.author.name if article.author else None,
        url=article.url,
        published_at=article.published_at,
        html=article.content,
    )


def _dominant_language(articles: list[Article]) -> str:
    counts = Counter(article.original_lang.value for article in articles)
    return counts.most_common(1)[0][0] if counts else _FALLBACK_LANGUAGE
