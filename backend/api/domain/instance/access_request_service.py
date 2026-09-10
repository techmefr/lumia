from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.domain.instance.exceptions import (
    AccessRequestAlreadyDecidedError,
    AccessRequestNotFoundError,
    AccessRequestsClosedError,
    EmailAlreadyRegisteredError,
)
from api.domain.instance.models import AccessMode, AccessRequest, AccessRequestStatus
from api.domain.instance.settings_service import get_instance
from api.domain.user.invitation_service import ensure_room_for_one_more_account
from api.domain.user.models import Role, User


async def request_access(session: AsyncSession, email: str, username: str) -> AccessRequest:
    instance = await get_instance(session)
    if instance.access_mode != AccessMode.ON_APPROVAL:
        raise AccessRequestsClosedError

    if await _is_email_taken(session, email):
        raise EmailAlreadyRegisteredError

    access_request = AccessRequest(email=email, username=username)
    session.add(access_request)
    await session.commit()
    return access_request


async def list_access_requests(
    session: AsyncSession, status: AccessRequestStatus | None = None
) -> list[AccessRequest]:
    query = select(AccessRequest).order_by(AccessRequest.created_at.desc())
    if status is not None:
        query = query.where(AccessRequest.status == status)
    return list(await session.scalars(query))


async def approve_access_request(session: AsyncSession, request_id: UUID, decided_by: User) -> User:
    """Turns an approved request into a real account, without a password.

    The account is created passwordless on purpose: the admin has no business choosing someone
    else's password, and the passwordless sign-in already covers a first connection by email.
    """
    access_request = await _get_pending_request(session, request_id)
    instance = await get_instance(session)
    await ensure_room_for_one_more_account(session, instance)

    if await _is_email_taken(session, access_request.email, ignore_request_id=request_id):
        raise EmailAlreadyRegisteredError

    account = User(
        instance_id=instance.id,
        email=access_request.email,
        username=access_request.username,
        role=Role.MEMBER,
    )
    session.add(account)
    _mark_decided(access_request, AccessRequestStatus.APPROVED, decided_by)
    await session.commit()
    return account


async def reject_access_request(
    session: AsyncSession, request_id: UUID, decided_by: User
) -> AccessRequest:
    access_request = await _get_pending_request(session, request_id)
    _mark_decided(access_request, AccessRequestStatus.REJECTED, decided_by)
    await session.commit()
    return access_request


def _mark_decided(
    access_request: AccessRequest, status: AccessRequestStatus, decided_by: User
) -> None:
    access_request.status = status
    access_request.decided_at = datetime.now(UTC)
    access_request.decided_by_id = decided_by.id


async def _get_pending_request(session: AsyncSession, request_id: UUID) -> AccessRequest:
    access_request = await session.get(AccessRequest, request_id)
    if access_request is None:
        raise AccessRequestNotFoundError
    if access_request.status != AccessRequestStatus.PENDING:
        raise AccessRequestAlreadyDecidedError
    return access_request


async def _is_email_taken(
    session: AsyncSession, email: str, *, ignore_request_id: UUID | None = None
) -> bool:
    if await session.scalar(select(User).where(User.email == email)) is not None:
        return True
    query = select(AccessRequest).where(AccessRequest.email == email)
    if ignore_request_id is not None:
        query = query.where(AccessRequest.id != ignore_request_id)
    return await session.scalar(query) is not None
