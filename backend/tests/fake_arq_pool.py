from typing import Any


class FakeArqPool:
    """The slice of redis and arq the reading-list import touches, held in memory."""

    def __init__(self) -> None:
        self.hashes: dict[str, dict[str, str]] = {}
        self.enqueued: list[tuple[str, tuple[Any, ...], dict[str, Any]]] = []

    async def hset(self, name: str, mapping: dict[str, str | int]) -> int:
        self.hashes.setdefault(name, {}).update({k: str(v) for k, v in mapping.items()})
        return len(mapping)

    async def hincrby(self, name: str, key: str, amount: int = 1) -> int:
        bucket = self.hashes.setdefault(name, {})
        bucket[key] = str(int(bucket.get(key, "0")) + amount)
        return int(bucket[key])

    async def hgetall(self, name: str) -> dict[bytes, bytes]:
        return {k.encode(): v.encode() for k, v in self.hashes.get(name, {}).items()}

    async def expire(self, name: str, time: int) -> bool:
        return name in self.hashes

    async def enqueue_job(self, function: str, *args: Any, **kwargs: Any) -> None:
        self.enqueued.append((function, args, kwargs))
