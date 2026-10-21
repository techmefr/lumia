import hashlib
import secrets

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from api.domain.fever.models import FeverKey
from api.domain.user.models import User
from api.technical.auth.tokens import hash_token


def derive_api_key(email: str, secret: str) -> str:
    """What a Fever client sends: the protocol fixes md5 over `email:password`."""
    return hashlib.md5(f"{email}:{secret}".encode(), usedforsecurity=False).hexdigest()


async def get_key(session: AsyncSession, user: User) -> FeverKey | None:
    keys = await session.scalars(select(FeverKey).where(FeverKey.user_id == user.id))
    return keys.first()


async def issue_key(session: AsyncSession, user: User) -> tuple[FeverKey, str]:
    """Draws a new secret, retiring the previous one; the secret is returned this once only."""
    await session.execute(delete(FeverKey).where(FeverKey.user_id == user.id))
    secret = secrets.token_urlsafe(24)
    key = FeverKey(user_id=user.id, key_hash=hash_token(derive_api_key(user.email, secret)))
    session.add(key)
    await session.commit()
    return key, secret


async def revoke_key(session: AsyncSession, user: User) -> None:
    await session.execute(delete(FeverKey).where(FeverKey.user_id == user.id))
    await session.commit()


async def authenticate(session: AsyncSession, api_key: str) -> User | None:
    users = await session.scalars(
        select(User)
        .join(FeverKey, FeverKey.user_id == User.id)
        .where(FeverKey.key_hash == hash_token(api_key.strip().lower()))
    )
    return users.first()
