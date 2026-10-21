from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from api.domain.export.models import ExportJob, ExportKind
from api.domain.user.account_service import delete_account
from api.domain.user.models import Instance, Role, User
from config.database import get_engine


@pytest.fixture
async def session(db_schema: None) -> AsyncIterator[AsyncSession]:
    session_factory = async_sessionmaker(get_engine(), expire_on_commit=False)
    async with session_factory() as db_session:
        yield db_session


async def test_deleting_an_account_takes_its_exported_files_with_it(
    session: AsyncSession,
) -> None:
    instance = Instance(max_accounts=10, disk_quota_mb=1000)
    session.add(instance)
    await session.flush()
    admin = User(
        instance_id=instance.id, email="admin@example.com", username="admin", role=Role.ADMIN
    )
    leaving = User(instance_id=instance.id, email="leaving@example.com", username="leaving")
    staying = User(instance_id=instance.id, email="staying@example.com", username="staying")
    session.add_all([admin, leaving, staying])
    await session.flush()
    for owner in (leaving, staying):
        session.add(
            ExportJob(
                user_id=owner.id,
                kind=ExportKind.PLAYLIST_EPUB,
                subject_id=uuid4(),
                expires_at=datetime.now(UTC) + timedelta(hours=1),
            )
        )
    await session.commit()

    await delete_account(session, leaving.id)
    await session.commit()

    owners = list(await session.scalars(select(ExportJob.user_id)))
    assert owners == [staying.id]
