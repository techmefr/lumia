from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from api.domain.user.models import Role, User
from api.technical.auth.jwt import InvalidAccessTokenError, decode_access_token
from api.technical.db import get_db_session

_bearer = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer),
    session: AsyncSession = Depends(get_db_session),
) -> User:
    try:
        user_id = decode_access_token(credentials.credentials)
    except InvalidAccessTokenError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED) from exc
    user = await session.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
    return user


async def require_admin(user: User = Depends(get_current_user)) -> User:
    if user.role != Role.ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
    return user
