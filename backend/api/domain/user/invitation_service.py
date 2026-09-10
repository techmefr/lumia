from collections.abc import Sequence
from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from api.domain.user.exceptions import (
    EmailAlreadyTakenError,
    InstanceFullError,
    InvalidInvitationError,
)
from api.domain.user.models import Instance, Invitation, Role, User
from api.technical.auth.hashing import hash_password
from api.technical.auth.tokens import generate_opaque_token, hash_token
from api.technical.email.smtp import send_email
from config.auth import get_auth_config
from config.email import get_email_config


async def count_accounts(session: AsyncSession, instance_id: UUID) -> int:
    return (
        await session.scalar(
            select(func.count()).select_from(User).where(User.instance_id == instance_id)
        )
        or 0
    )


async def ensure_room_for_one_more_account(session: AsyncSession, instance: Instance) -> None:
    """Raises when the instance already holds every account its admin allowed."""
    if await count_accounts(session, instance.id) >= instance.max_accounts:
        raise InstanceFullError


async def invite_member(
    session: AsyncSession, instance: Instance, *, email: str, role: Role = Role.MEMBER
) -> Invitation:
    """Creates a single-use invitation and mails its link to the address.

    Pending invitations count against `max_accounts`: an admin who has already promised the last
    two seats should not be told there is room for a third.
    """
    if await session.scalar(select(User).where(User.email == email)) is not None:
        raise EmailAlreadyTakenError
    taken = await count_accounts(session, instance.id) + await _count_pending(session, instance.id)
    if taken >= instance.max_accounts:
        raise InstanceFullError

    raw_token = generate_opaque_token()
    config = get_auth_config()
    invitation = Invitation(
        instance_id=instance.id,
        email=email,
        role=role,
        token=hash_token(raw_token),
        expires_at=datetime.now(UTC) + timedelta(days=config.invitation_ttl_days),
    )
    session.add(invitation)
    await session.commit()

    frontend_url = get_email_config().frontend_url.rstrip("/")
    await send_email(
        to=email,
        subject="Vous êtes invité sur Lumia",
        body=(
            "Cliquez sur ce lien pour créer votre compte : "
            f"{frontend_url}/invitation?token={raw_token}"
        ),
    )
    return invitation


async def list_pending_invitations(
    session: AsyncSession, instance_id: UUID
) -> Sequence[Invitation]:
    result = await session.scalars(_pending(instance_id).order_by(Invitation.created_at.desc()))
    return result.all()


async def revoke_invitation(session: AsyncSession, instance_id: UUID, invitation_id: UUID) -> None:
    invitation = await session.scalar(
        select(Invitation).where(
            Invitation.id == invitation_id, Invitation.instance_id == instance_id
        )
    )
    if invitation is None:
        raise InvalidInvitationError
    invitation.revoked_at = datetime.now(UTC)
    await session.commit()


async def accept_invitation(
    session: AsyncSession, raw_token: str, *, username: str, password: str
) -> User:
    """Turns an invitation into an account, spending the token."""
    invitation = await session.scalar(
        select(Invitation).where(Invitation.token == hash_token(raw_token))
    )
    if (
        invitation is None
        or invitation.accepted_at is not None
        or invitation.revoked_at is not None
        or invitation.expires_at < datetime.now(UTC)
    ):
        raise InvalidInvitationError
    if await session.scalar(select(User).where(User.email == invitation.email)) is not None:
        raise EmailAlreadyTakenError

    instance = await session.get(Instance, invitation.instance_id)
    if instance is None:
        raise InvalidInvitationError
    # Checked again here and not only at invite time: seats can have filled up in between, and an
    # invitation that outlives the room it was promised must not push the instance over its cap.
    await ensure_room_for_one_more_account(session, instance)

    user = User(
        instance_id=invitation.instance_id,
        email=invitation.email,
        username=username,
        password_hash=hash_password(password),
        role=invitation.role,
    )
    session.add(user)
    invitation.accepted_at = datetime.now(UTC)
    await session.commit()
    return user


async def _count_pending(session: AsyncSession, instance_id: UUID) -> int:
    return (
        await session.scalar(select(func.count()).select_from(_pending(instance_id).subquery()))
        or 0
    )


def _pending(instance_id: UUID) -> Select[tuple[Invitation]]:
    return select(Invitation).where(
        Invitation.instance_id == instance_id,
        Invitation.accepted_at.is_(None),
        Invitation.revoked_at.is_(None),
        Invitation.expires_at > datetime.now(UTC),
    )
