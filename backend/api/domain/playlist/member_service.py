from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.domain.playlist.exceptions import (
    CannotShareWithOwnerError,
    MembershipNotFoundError,
    MemberUserNotFoundError,
    PlaylistForbiddenError,
)
from api.domain.playlist.models import MemberRole, Playlist, PlaylistMember, PlaylistRole
from api.domain.playlist.playlist_service import get_playlist, role_on
from api.domain.user.models import User


async def share_with(
    session: AsyncSession,
    owner_id: UUID,
    playlist_id: UUID,
    *,
    email: str,
    role: MemberRole,
) -> Playlist:
    """Grants a role to an existing account of the owner's instance, or changes the one it holds.

    Anyone unknown to the instance, or living on another one, is the same not-found: a playlist
    never travels outside the instance it was made on, and no account is invented by sharing.
    """
    playlist = await get_playlist(session, owner_id, playlist_id, PlaylistRole.OWNER)
    owner = await session.get(User, owner_id)
    invitee = await session.scalar(
        select(User).where(
            User.email == email.strip().lower(),
            User.instance_id == (owner.instance_id if owner else None),
        )
    )
    if invitee is None:
        raise MemberUserNotFoundError
    if invitee.id == playlist.user_id:
        raise CannotShareWithOwnerError

    existing = next((member for member in playlist.members if member.user_id == invitee.id), None)
    if existing is None:
        session.add(PlaylistMember(playlist_id=playlist.id, user_id=invitee.id, role=role))
    else:
        existing.role = role
    await session.commit()
    await session.refresh(playlist, ["members"])
    return playlist


async def revoke(
    session: AsyncSession, requester_id: UUID, playlist_id: UUID, member_id: UUID
) -> None:
    """The owner removes anyone; a member can only remove themselves, which is leaving."""
    playlist = await get_playlist(session, requester_id, playlist_id)
    if role_on(playlist, requester_id) != PlaylistRole.OWNER and member_id != requester_id:
        raise PlaylistForbiddenError

    member = next((m for m in playlist.members if m.user_id == member_id), None)
    if member is None:
        raise MembershipNotFoundError
    await session.delete(member)
    await session.commit()


async def usernames(session: AsyncSession, user_ids: set[UUID]) -> dict[UUID, str]:
    if not user_ids:
        return {}
    rows = await session.execute(select(User.id, User.username).where(User.id.in_(user_ids)))
    return {user_id: username for user_id, username in rows}
