from typing import Protocol
from uuid import UUID

from api.domain.article.exceptions import ImportNotFoundError

_KEY_PREFIX = "reading-import"
_RETENTION_SECONDS = 24 * 60 * 60


class ProgressRedis(Protocol):
    async def hset(self, name: str, mapping: dict[str, str | int]) -> int: ...
    async def hincrby(self, name: str, key: str, amount: int = 1) -> int: ...
    async def hgetall(self, name: str) -> dict[bytes, bytes]: ...
    async def expire(self, name: str, time: int) -> bool: ...


def _key(import_id: str) -> str:
    return f"{_KEY_PREFIX}:{import_id}"


async def start_progress(redis: ProgressRedis, import_id: str, user_id: UUID, total: int) -> None:
    await redis.hset(
        _key(import_id), {"user_id": str(user_id), "total": total, "saved": 0, "failed": 0}
    )
    await redis.expire(_key(import_id), _RETENTION_SECONDS)


async def reset_counts(redis: ProgressRedis, import_id: str) -> None:
    """A retried job starts over, otherwise the links it already handled would be counted twice."""
    await redis.hset(_key(import_id), {"saved": 0, "failed": 0})


async def record_outcome(redis: ProgressRedis, import_id: str, *, saved: bool) -> None:
    await redis.hincrby(_key(import_id), "saved" if saved else "failed", 1)


async def read_progress(
    redis: ProgressRedis, import_id: str, user_id: UUID
) -> dict[str, int | bool]:
    raw = await redis.hgetall(_key(import_id))
    fields = {key.decode(): value.decode() for key, value in raw.items()}
    if fields.get("user_id") != str(user_id):
        raise ImportNotFoundError
    total, saved, failed = int(fields["total"]), int(fields["saved"]), int(fields["failed"])
    return {
        "total": total,
        "saved": saved,
        "failed": failed,
        "finished": saved + failed >= total,
    }
