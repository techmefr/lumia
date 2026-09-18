import hashlib
import hmac

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from api.domain.fever.models import FeverApiKey
from api.domain.user.models import User
from api.technical.auth.tokens import generate_opaque_token


def _fever_digest(email: str, token: str) -> str:
    """The literal Fever `api_key` value: md5(email:token), lowercase hex.

    Fever clients compute md5(username:password) themselves and send only the digest, so the
    server must be able to reproduce the same digest from what it hands out as the "password" (the
    opaque token) to recognise a matching request. md5 is part of the wire protocol, not a security
    choice of ours: nothing sensitive is protected by it, since the input token is high-entropy and
    single-purpose.
    """
    return hashlib.md5(f"{email}:{token}".encode()).hexdigest()


async def issue_api_key(session: AsyncSession, user: User) -> str:
    """Mints a new Fever token for the user, replacing any previous one, and returns it in the
    clear. Only its digest is persisted; the caller must hand the plaintext to the user now, since
    it cannot be recovered afterwards."""
    token = generate_opaque_token()
    digest = _fever_digest(user.email, token)

    existing = await session.scalar(select(FeverApiKey).where(FeverApiKey.user_id == user.id))
    if existing is None:
        session.add(FeverApiKey(user_id=user.id, digest=digest))
    else:
        existing.digest = digest
    await session.commit()
    return token


async def revoke_api_key(session: AsyncSession, user: User) -> None:
    await session.execute(delete(FeverApiKey).where(FeverApiKey.user_id == user.id))
    await session.commit()


async def has_api_key(session: AsyncSession, user: User) -> bool:
    key = await session.scalar(select(FeverApiKey).where(FeverApiKey.user_id == user.id))
    return key is not None


async def resolve_user_by_api_key(session: AsyncSession, api_key: str) -> User | None:
    """Finds the account whose stored digest matches the api_key a client just sent."""
    if not api_key:
        return None
    key = await session.scalar(select(FeverApiKey).where(FeverApiKey.digest == api_key.lower()))
    if key is None or not hmac.compare_digest(key.digest, api_key.lower()):
        return None
    return await session.get(User, key.user_id)
