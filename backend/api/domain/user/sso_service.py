from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.domain.user.exceptions import SsoNotConfiguredError
from api.domain.user.models import Instance, Role, User


def ensure_sso_configured(instance: Instance) -> None:
    if instance.oidc_issuer is None:
        raise SsoNotConfiguredError


async def get_or_create_sso_user(
    session: AsyncSession, instance: Instance, *, sub: str, email: str
) -> User:
    existing = await session.scalar(select(User).where(User.sso_subject == sub))
    if existing is not None:
        return existing

    user = User(
        instance_id=instance.id,
        email=email,
        username=email.split("@", 1)[0],
        password_hash=None,
        sso_subject=sub,
        role=Role.MEMBER,
    )
    session.add(user)
    await session.commit()
    return user
