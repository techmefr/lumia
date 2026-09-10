from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from api.domain.user.exceptions import (
    EmailAlreadyTakenError,
    InstanceFullError,
    InvalidInvitationError,
)
from api.domain.user.invitation_service import (
    accept_invitation,
    invite_member,
    list_pending_invitations,
    revoke_invitation,
)
from api.domain.user.models import Instance, Invitation, Role, User
from api.technical.auth.hashing import verify_password
from api.technical.auth.tokens import hash_token
from config.database import get_engine


@pytest.fixture
async def session(db_schema: None) -> AsyncIterator[AsyncSession]:
    session_factory = async_sessionmaker(get_engine(), expire_on_commit=False)
    async with session_factory() as db_session:
        yield db_session


async def _create_instance(session: AsyncSession, *, max_accounts: int = 10) -> Instance:
    instance = Instance(max_accounts=max_accounts, disk_quota_mb=1000)
    session.add(instance)
    await session.commit()
    return instance


async def _add_user(session: AsyncSession, instance: Instance, email: str) -> User:
    user = User(instance_id=instance.id, email=email, username="someone")
    session.add(user)
    await session.commit()
    return user


async def _invite(
    session: AsyncSession,
    instance: Instance,
    *,
    email: str = "invited@example.com",
    role: Role = Role.MEMBER,
    raw_token: str = "the-raw-token",
) -> Invitation:
    with (
        patch("api.domain.user.invitation_service.send_email", new_callable=AsyncMock),
        patch(
            "api.domain.user.invitation_service.generate_opaque_token",
            return_value=raw_token,
        ),
    ):
        return await invite_member(session, instance, email=email, role=role)


async def test_inviting_mails_a_redeemable_link_to_the_address(session: AsyncSession) -> None:
    instance = await _create_instance(session)
    with (
        patch("api.domain.user.invitation_service.send_email", new_callable=AsyncMock) as mock_send,
        patch(
            "api.domain.user.invitation_service.generate_opaque_token",
            return_value="the-raw-token",
        ),
    ):
        await invite_member(session, instance, email="invited@example.com")

    assert mock_send.await_args is not None
    assert mock_send.await_args.kwargs["to"] == "invited@example.com"
    assert (
        "http://localhost:8080/invitation?token=the-raw-token"
        in mock_send.await_args.kwargs["body"]
    )


async def test_the_stored_invitation_holds_only_the_hash_of_the_token(
    session: AsyncSession,
) -> None:
    """A dump of the table must not be enough to redeem an invitation."""
    instance = await _create_instance(session)
    invitation = await _invite(session, instance)

    assert invitation.token == hash_token("the-raw-token")


async def test_inviting_an_address_that_already_has_an_account_is_refused(
    session: AsyncSession,
) -> None:
    instance = await _create_instance(session)
    await _add_user(session, instance, "member@example.com")

    with pytest.raises(EmailAlreadyTakenError):
        await _invite(session, instance, email="member@example.com")


async def test_inviting_is_refused_once_the_accounts_fill_the_instance(
    session: AsyncSession,
) -> None:
    instance = await _create_instance(session, max_accounts=1)
    await _add_user(session, instance, "admin@example.com")

    with pytest.raises(InstanceFullError):
        await _invite(session, instance)


async def test_pending_invitations_count_against_the_ceiling(session: AsyncSession) -> None:
    """Otherwise an admin could promise ten seats on a two-seat instance."""
    instance = await _create_instance(session, max_accounts=2)
    await _add_user(session, instance, "admin@example.com")
    await _invite(session, instance, email="first@example.com", raw_token="first")

    with pytest.raises(InstanceFullError):
        await _invite(session, instance, email="second@example.com", raw_token="second")


async def test_a_revoked_invitation_frees_the_seat_it_held(session: AsyncSession) -> None:
    instance = await _create_instance(session, max_accounts=2)
    await _add_user(session, instance, "admin@example.com")
    invitation = await _invite(session, instance, email="first@example.com", raw_token="first")

    await revoke_invitation(session, instance.id, invitation.id)

    await _invite(session, instance, email="second@example.com", raw_token="second")


async def test_accepting_creates_a_member_who_can_sign_in_with_the_chosen_password(
    session: AsyncSession,
) -> None:
    instance = await _create_instance(session)
    await _invite(session, instance)

    user = await accept_invitation(
        session, "the-raw-token", username="reader", password="correct-horse-battery-staple"
    )

    assert user.email == "invited@example.com"
    assert user.username == "reader"
    assert user.role == Role.MEMBER
    assert user.password_hash is not None
    assert verify_password("correct-horse-battery-staple", user.password_hash)


async def test_accepting_grants_the_role_the_admin_chose(session: AsyncSession) -> None:
    instance = await _create_instance(session)
    await _invite(session, instance, role=Role.ADMIN)

    user = await accept_invitation(
        session, "the-raw-token", username="second-admin", password="correct-horse-battery-staple"
    )

    assert user.role == Role.ADMIN


async def test_an_invitation_can_only_be_accepted_once(session: AsyncSession) -> None:
    instance = await _create_instance(session)
    await _invite(session, instance)
    await accept_invitation(
        session, "the-raw-token", username="reader", password="correct-horse-battery-staple"
    )

    with pytest.raises(InvalidInvitationError):
        await accept_invitation(
            session, "the-raw-token", username="thief", password="correct-horse-battery-staple"
        )


async def test_accepting_an_unknown_token_is_refused(session: AsyncSession) -> None:
    with pytest.raises(InvalidInvitationError):
        await accept_invitation(
            session, "never-issued", username="reader", password="correct-horse-battery-staple"
        )


async def test_accepting_a_revoked_invitation_is_refused(session: AsyncSession) -> None:
    instance = await _create_instance(session)
    invitation = await _invite(session, instance)
    await revoke_invitation(session, instance.id, invitation.id)

    with pytest.raises(InvalidInvitationError):
        await accept_invitation(
            session, "the-raw-token", username="reader", password="correct-horse-battery-staple"
        )


async def test_accepting_an_expired_invitation_is_refused(session: AsyncSession) -> None:
    instance = await _create_instance(session)
    session.add(
        Invitation(
            instance_id=instance.id,
            email="invited@example.com",
            token=hash_token("stale-token"),
            expires_at=datetime.now(UTC) - timedelta(days=1),
        )
    )
    await session.commit()

    with pytest.raises(InvalidInvitationError):
        await accept_invitation(
            session, "stale-token", username="reader", password="correct-horse-battery-staple"
        )


async def test_accepting_is_refused_when_the_seats_filled_up_in_the_meantime(
    session: AsyncSession,
) -> None:
    instance = await _create_instance(session, max_accounts=2)
    await _add_user(session, instance, "admin@example.com")
    await _invite(session, instance)
    await _add_user(session, instance, "walked-in@example.com")

    with pytest.raises(InstanceFullError):
        await accept_invitation(
            session, "the-raw-token", username="reader", password="correct-horse-battery-staple"
        )


async def test_accepting_is_refused_when_the_address_signed_up_another_way(
    session: AsyncSession,
) -> None:
    instance = await _create_instance(session)
    await _invite(session, instance)
    await _add_user(session, instance, "invited@example.com")

    with pytest.raises(EmailAlreadyTakenError):
        await accept_invitation(
            session, "the-raw-token", username="reader", password="correct-horse-battery-staple"
        )


async def test_listing_returns_the_invitations_still_open(session: AsyncSession) -> None:
    instance = await _create_instance(session)
    await _invite(session, instance, email="open@example.com", raw_token="open")
    accepted = await _invite(session, instance, email="joined@example.com", raw_token="joined")
    await accept_invitation(
        session, "joined", username="reader", password="correct-horse-battery-staple"
    )
    revoked = await _invite(session, instance, email="dropped@example.com", raw_token="dropped")
    await revoke_invitation(session, instance.id, revoked.id)

    pending = await list_pending_invitations(session, instance.id)

    assert [invitation.email for invitation in pending] == ["open@example.com"]
    assert accepted.accepted_at is not None


async def test_listing_ignores_the_invitations_of_another_instance(session: AsyncSession) -> None:
    instance = await _create_instance(session)
    other = await _create_instance(session)
    await _invite(session, other, email="theirs@example.com")

    assert await list_pending_invitations(session, instance.id) == []


async def test_revoking_an_invitation_of_another_instance_is_refused(
    session: AsyncSession,
) -> None:
    instance = await _create_instance(session)
    other = await _create_instance(session)
    theirs = await _invite(session, other, email="theirs@example.com")

    with pytest.raises(InvalidInvitationError):
        await revoke_invitation(session, instance.id, theirs.id)


async def test_revoking_an_unknown_invitation_is_refused(session: AsyncSession) -> None:
    instance = await _create_instance(session)

    with pytest.raises(InvalidInvitationError):
        await revoke_invitation(session, instance.id, uuid4())
