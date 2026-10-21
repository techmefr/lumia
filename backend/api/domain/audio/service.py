import hashlib
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from api.domain.audio.models import ArticleAudio
from worker.technical.speech.base import SynthesizedAudio

BYTES_PER_MB = 1024 * 1024


def voice_hash(cache_key: str) -> str:
    return hashlib.sha256(cache_key.encode()).hexdigest()


async def find_cached_audio(
    session: AsyncSession, *, user_id: UUID, article_id: UUID, voice: str
) -> ArticleAudio | None:
    result = await session.scalars(
        select(ArticleAudio).where(
            ArticleAudio.user_id == user_id,
            ArticleAudio.article_id == article_id,
            ArticleAudio.voice_hash == voice,
        )
    )
    return result.first()


async def store_audio(
    session: AsyncSession,
    *,
    user_id: UUID,
    article_id: UUID,
    voice: str,
    audio: SynthesizedAudio,
    cache_limit_mb: int,
) -> None:
    """Keeps the reading, then drops the account's oldest ones until it is back under its ceiling.

    Two requests racing on the same article both synthesise; the second insert is ignored rather
    than failing a reader who has already been served.
    """
    await session.execute(
        insert(ArticleAudio)
        .values(
            user_id=user_id,
            article_id=article_id,
            voice_hash=voice,
            content_type=audio.content_type,
            size_bytes=len(audio.data),
            data=audio.data,
        )
        .on_conflict_do_nothing(constraint="uq_article_audios_voice")
    )
    await _evict_beyond(session, user_id=user_id, limit_bytes=cache_limit_mb * BYTES_PER_MB)
    await session.commit()


async def _evict_beyond(session: AsyncSession, *, user_id: UUID, limit_bytes: int) -> None:
    rows = (
        await session.execute(
            select(ArticleAudio.id, ArticleAudio.size_bytes)
            .where(ArticleAudio.user_id == user_id)
            .order_by(ArticleAudio.created_at.desc())
        )
    ).all()
    kept = 0
    expired: list[UUID] = []
    for audio_id, size in rows:
        kept += size
        if kept > limit_bytes:
            expired.append(audio_id)
    if expired:
        await session.execute(delete(ArticleAudio).where(ArticleAudio.id.in_(expired)))
