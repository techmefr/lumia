from sqlalchemy.ext.asyncio import AsyncSession

from worker.technical.db import worker_session


async def test_worker_session_yields_an_async_session() -> None:
    async with worker_session() as session:
        assert isinstance(session, AsyncSession)
