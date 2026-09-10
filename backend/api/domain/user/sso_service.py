from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.domain.user.exceptions import SsoNotConfiguredError, SsoSubjectMismatchError
from api.domain.user.invitation_service import ensure_room_for_one_more_account
from api.domain.user.models import Instance, Role, User


@dataclass(frozen=True)
class SsoConfiguration:
    """The four OIDC settings an instance needs, once they are known to be present.

    The columns are all nullable — an instance may simply not use SSO — so the flows used to carry
    that uncertainty all the way down and paper over it with asserts. Reading the configuration
    once, here, is what makes the rest of the flow able to state its inputs.
    """

    issuer: str
    client_id: str
    client_secret_encrypted: str
    redirect_uri: str


def read_sso_configuration(instance: Instance) -> SsoConfiguration:
    if (
        instance.oidc_issuer is None
        or instance.oidc_client_id is None
        or instance.oidc_client_secret_encrypted is None
        or instance.oidc_redirect_uri is None
    ):
        raise SsoNotConfiguredError

    return SsoConfiguration(
        issuer=instance.oidc_issuer,
        client_id=instance.oidc_client_id,
        client_secret_encrypted=instance.oidc_client_secret_encrypted,
        redirect_uri=instance.oidc_redirect_uri,
    )


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
        # provider is not a reason to remove a way in. No seat is taken either, so this runs
        # before the ceiling check: a full instance must still let its own readers in.
        by_email.sso_subject = sub
        await session.commit()
        return by_email

    # Anyone the provider accepts lands here, so this is where the instance's ceiling has to hold:
    # without it `max_accounts` would mean nothing as soon as SSO is switched on.
    await ensure_room_for_one_more_account(session, instance)
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
