from collections.abc import AsyncIterator
from uuid import uuid4

import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from api.domain.user.models import Instance, Role, User
from api.technical.auth.jwt import create_access_token
from api.technical.auth.middleware import get_current_user, require_admin
from config.database import get_engine


def _bearer(token: str) -> HTTPAuthorizationCredentials:
    return HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)


@pytest.fixture
async def session(db_schema: None) -> AsyncIterator[AsyncSession]:
    session_factory = async_sessionmaker(get_engine(), expire_on_commit=False)
    async with session_factory() as db_session:
        yield db_session


async def _create_user(session: AsyncSession, role: Role) -> User:
    instance = Instance(max_accounts=10, disk_quota_mb=1000)
    session.add(instance)
    await session.flush()
    user = User(
        instance_id=instance.id,
        email=f"{uuid4()}@example.com",
        username="member",
        password_hash="irrelevant",
        role=role,
    )
    session.add(user)
    await session.commit()
    return user


async def test_get_current_user_returns_the_user_from_a_valid_token(
    session: AsyncSession,
) -> None:
    user = await _create_user(session, Role.MEMBER)
    token = create_access_token(user.id)
    resolved = await get_current_user(credentials=_bearer(token), session=session)
    assert resolved.id == user.id


async def test_get_current_user_rejects_an_invalid_token(session: AsyncSession) -> None:
    with pytest.raises(HTTPException) as exc_info:
        await get_current_user(credentials=_bearer("not-a-jwt"), session=session)
    assert exc_info.value.status_code == 401


async def test_get_current_user_rejects_a_token_for_a_deleted_user(
    session: AsyncSession,
) -> None:
    token = create_access_token(uuid4())
    with pytest.raises(HTTPException) as exc_info:
        await get_current_user(credentials=_bearer(token), session=session)
    assert exc_info.value.status_code == 401


async def test_require_admin_accepts_an_admin_user(session: AsyncSession) -> None:
    admin = await _create_user(session, Role.ADMIN)
    resolved = await require_admin(user=admin)
    assert resolved.id == admin.id


async def test_require_admin_rejects_a_member_user(session: AsyncSession) -> None:
    member = await _create_user(session, Role.MEMBER)
    with pytest.raises(HTTPException) as exc_info:
        await require_admin(user=member)
    assert exc_info.value.status_code == 403
