from arq.connections import ArqRedis

from worker.technical.queue import get_arq_pool


async def test_get_arq_pool_returns_the_same_pool_on_repeated_calls() -> None:
    first = await get_arq_pool()
    second = await get_arq_pool()
    assert first is second
    assert isinstance(first, ArqRedis)
