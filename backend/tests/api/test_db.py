from sqlalchemy.ext.asyncio import AsyncSession

from api.technical.db import get_db_session


async def test_get_db_session_yields_an_async_session() -> None:
    session_generator = get_db_session()
    session = await session_generator.__anext__()
    assert isinstance(session, AsyncSession)
    await session.close()
