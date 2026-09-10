from collections.abc import AsyncIterator

import httpx
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from api.domain.user.models import Instance, Role, User
from api.main import app
from api.technical.auth.jwt import create_access_token
from config.database import get_engine

ADMIN_PAYLOAD = {
    "email": "admin@example.com",
    "username": "admin",
    "password": "correct-horse-battery-staple",
}


@pytest.fixture
async def client(db_schema: None) -> AsyncIterator[httpx.AsyncClient]:
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as async_client:
        yield async_client


@pytest.fixture
async def session(db_schema: None) -> AsyncIterator[AsyncSession]:
    session_factory = async_sessionmaker(get_engine(), expire_on_commit=False)
    async with session_factory() as db_session:
        yield db_session


@pytest.fixture
async def admin_headers(client: httpx.AsyncClient) -> dict[str, str]:
    response = await client.post("/onboarding/admin", json=ADMIN_PAYLOAD)
    assert response.status_code == 201
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


async def add_member(session: AsyncSession, email: str = "membre@example.com") -> User:
    """A second account signed in as a member, which no public route can create on its own."""
    instance = await session.scalar(select(Instance))
    assert instance is not None
    member = User(instance_id=instance.id, email=email, username="membre", role=Role.MEMBER)
    session.add(member)
    await session.commit()
    return member


def headers_for(user: User) -> dict[str, str]:
    return {"Authorization": f"Bearer {create_access_token(user.id)}"}
