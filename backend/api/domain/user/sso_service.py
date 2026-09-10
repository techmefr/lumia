from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.domain.user.exceptions import SsoNotConfiguredError, SsoSubjectMismatchError
from api.domain.user.models import Instance, Role, User


def ensure_sso_configured(instance: Instance) -> None:
    if instance.oidc_issuer is None:
        raise SsoNotConfiguredError


async def get_or_create_sso_user(
    session: AsyncSession, instance: Instance, *, sub: str, email: str
) -> User:
    """Finds the reader behind a provider's subject, linking or provisioning as needed.

    The subject comes first: it is the identifier the provider promises to keep stable, so a
    reader whose mailbox was renamed is still recognised. The address on file is deliberately
    left as it was — it is unique in this schema, and the new one may already belong to somebody
    else.
    """
    existing = await session.scalar(select(User).where(User.sso_subject == sub))
    if existing is not None:
        return existing

    by_email = await session.scalar(select(User).where(User.email == email))
    if by_email is not None:
        if by_email.sso_subject is not None:
            # Two subjects claiming one address: either the provider recycles addresses, or
            # somebody is trying to take the account over. Moving it to whoever asked last is
            # the one answer we must not give.
            raise SsoSubjectMismatchError
        # An account created before SSO was turned on. Their password is kept: linking a
        # provider is not a reason to remove a way in.
        by_email.sso_subject = sub
        await session.commit()
        return by_email

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
