from collections.abc import AsyncIterator
from datetime import UTC, datetime
from uuid import UUID, uuid4

import httpx
import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from api.domain.article.models import Article, ArticleKeyword, Keyword, Lang
from api.domain.feed.models import Feed, Folder, SourceType
from api.domain.playlist.models import Playlist, PlaylistItem
from api.domain.recommendation.models import (
    FilterMode,
    UserArticleFeedback,
    UserFilterRule,
    UserKeywordScore,
)
from api.domain.user.models import Role, User
from api.main import app
from api.technical.auth.hashing import hash_password
from api.technical.auth.jwt import create_access_token
from config.database import get_engine

PASSWORD = "correct-horse-battery-staple"
ADMIN_PAYLOAD = {"email": "admin@example.com", "username": "admin", "password": PASSWORD}


@pytest.fixture
async def client(db_schema: None) -> AsyncIterator[httpx.AsyncClient]:
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as async_client:
        yield async_client


def _session() -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(get_engine(), expire_on_commit=False)


async def _onboard(client: httpx.AsyncClient) -> dict[str, str]:
    response = await client.post("/onboarding/admin", json=ADMIN_PAYLOAD)
    assert response.status_code == 201
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


async def _fill_the_account(email: str = ADMIN_PAYLOAD["email"]) -> UUID:
    """Gives the account one of everything that hangs off a user, so a deletion has to face
    every reference in the schema rather than the easy half."""
    async with _session()() as session:
        user = (await session.scalars(select(User).where(User.email == email))).one()
        # Feeds, entries and keywords are unique across the instance, so each reader's fixture
        # needs its own values rather than a shared literal.
        own = email.split("@", 1)[0]
        folder = Folder(user_id=user.id, name="Tech")
        session.add(folder)
        await session.flush()
        feed = Feed(
            user_id=user.id,
            folder_id=folder.id,
            source_type=SourceType.MINIFLUX,
            external_feed_id=f"feed-{own}",
            title="A blog",
            url=f"https://{own}.test/rss",
        )
        session.add(feed)
        await session.flush()
        article = Article(
            feed_id=feed.id,
            external_entry_id=f"entry-{own}",
            title="An article",
            url=f"https://{own}.test/101",
            content="<p>Body</p>",
            published_at=datetime.now(UTC),
        )
        keyword = Keyword(term=f"rss-{own}", lang=Lang.FR)
        session.add_all([article, keyword])
        await session.flush()
        playlist = Playlist(user_id=user.id, name="Ce soir")
        session.add(playlist)
        await session.flush()
        session.add_all(
            [
                ArticleKeyword(article_id=article.id, keyword_id=keyword.id, weight=1.0),
                PlaylistItem(playlist_id=playlist.id, article_id=article.id, position=0),
                UserArticleFeedback(
                    user_id=user.id, article_id=article.id, saved=True, favorite=True
                ),
                UserFilterRule(user_id=user.id, term="crypto", mode=FilterMode.MUTE),
                UserKeywordScore(user_id=user.id, keyword_id=keyword.id, score=0.5),
            ]
        )
        await session.commit()
        return user.id


async def _add_member(email: str, *, role: Role = Role.MEMBER) -> UUID:
    async with _session()() as session:
        admin = (await session.scalars(select(User).where(User.role == Role.ADMIN))).first()
        assert admin is not None
        member = User(
            instance_id=admin.instance_id,
            email=email,
            username=email.split("@", 1)[0],
            password_hash=hash_password(PASSWORD),
            role=role,
        )
        session.add(member)
        await session.commit()
        return member.id


async def _count(model: type) -> int:
    async with _session()() as session:
        return await session.scalar(select(func.count()).select_from(model)) or 0


async def _login(client: httpx.AsyncClient, email: str) -> dict[str, str]:
    response = await client.post("/auth/login", json={"email": email, "password": PASSWORD})
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


async def test_the_export_returns_what_the_reader_put_in(client: httpx.AsyncClient) -> None:
    headers = await _onboard(client)
    await _fill_the_account()

    response = await client.get("/me/export", headers=headers)

    assert response.status_code == 200
    body = response.json()
    assert body["account"]["email"] == ADMIN_PAYLOAD["email"]
    assert [feed["title"] for feed in body["feeds"]] == ["A blog"]
    assert body["feeds"][0]["folder"] == "Tech"
    assert [rule["term"] for rule in body["filter_rules"]] == ["crypto"]
    assert [playlist["name"] for playlist in body["playlists"]] == ["Ce soir"]
    assert [article["title"] for article in body["playlists"][0]["articles"]] == ["An article"]
    assert [article["title"] for article in body["saved"]] == ["An article"]
    assert [article["title"] for article in body["favorites"]] == ["An article"]


async def test_the_export_carries_no_secret(client: httpx.AsyncClient) -> None:
    """It is a file the reader downloads and forwards; a key or a hash has no business in it."""
    headers = await _onboard(client)

    body = (await client.get("/me/export", headers=headers)).text

    assert "password" not in body
    assert "api_key" not in body


async def test_the_export_holds_only_the_calling_reader_s_data(
    client: httpx.AsyncClient,
) -> None:
    headers = await _onboard(client)
    await _fill_the_account()
    member_email = "member@example.com"
    await _add_member(member_email)

    response = await client.get("/me/export", headers=await _login(client, member_email))

    assert response.json()["feeds"] == []
    assert (await client.get("/me/export", headers=headers)).json()["feeds"] != []


async def test_the_export_requires_being_logged_in(client: httpx.AsyncClient) -> None:
    await _onboard(client)
    assert (await client.get("/me/export")).status_code == 401


async def test_deleting_an_account_takes_everything_that_hung_off_it(
    client: httpx.AsyncClient,
) -> None:
    await _onboard(client)
    await _fill_the_account()
    member_email = "leaving@example.com"
    await _add_member(member_email)
    headers = await _login(client, member_email)
    await _fill_the_account(member_email)

    response = await client.request(
        "DELETE",
        "/me",
        headers=headers,
        json={"confirm_email": member_email, "password": PASSWORD},
    )

    assert response.status_code == 204
    # One of each is left: the admin's, untouched.
    assert await _count(Feed) == 1
    assert await _count(Folder) == 1
    assert await _count(Article) == 1
    assert await _count(Playlist) == 1
    assert await _count(PlaylistItem) == 1
    assert await _count(ArticleKeyword) == 1
    assert await _count(UserArticleFeedback) == 1
    assert await _count(UserFilterRule) == 1
    assert await _count(UserKeywordScore) == 1
    assert await _count(User) == 1


async def test_a_deleted_account_can_no_longer_sign_in(client: httpx.AsyncClient) -> None:
    await _onboard(client)
    member_email = "leaving@example.com"
    await _add_member(member_email)
    headers = await _login(client, member_email)

    await client.request(
        "DELETE",
        "/me",
        headers=headers,
        json={"confirm_email": member_email, "password": PASSWORD},
    )

    refused = await client.post("/auth/login", json={"email": member_email, "password": PASSWORD})
    assert refused.status_code == 401
    assert (await client.get("/me", headers=headers)).status_code == 401


async def test_deleting_needs_the_account_s_own_address(client: httpx.AsyncClient) -> None:
    headers = await _onboard(client)

    response = await client.request(
        "DELETE",
        "/me",
        headers=headers,
        json={"confirm_email": "someone-else@example.com", "password": PASSWORD},
    )

    assert response.status_code == 400
    assert await _count(User) == 1


async def test_deleting_needs_the_password_when_the_account_has_one(
    client: httpx.AsyncClient,
) -> None:
    """An unlocked screen must not be enough to erase somebody's account."""
    await _onboard(client)
    member_email = "leaving@example.com"
    await _add_member(member_email)
    headers = await _login(client, member_email)

    for payload in (
        {"confirm_email": member_email},
        {"confirm_email": member_email, "password": "wrong-password"},
    ):
        response = await client.request("DELETE", "/me", headers=headers, json=payload)
        assert response.status_code == 401

    assert await _count(User) == 2


async def test_a_passwordless_account_is_deleted_on_the_address_alone(
    client: httpx.AsyncClient,
) -> None:
    """An SSO or magic-link account has no password to give, and refusing it would trap it."""
    await _onboard(client)
    member_email = "sso@example.com"
    member_id = await _add_member(member_email)
    async with _session()() as session:
        member = await session.get(User, member_id)
        assert member is not None
        member.password_hash = None
        await session.commit()
    headers = {"Authorization": f"Bearer {create_access_token(member_id)}"}

    response = await client.request(
        "DELETE", "/me", headers=headers, json={"confirm_email": member_email}
    )

    assert response.status_code == 204
    assert await _count(User) == 1


async def test_the_last_admin_cannot_delete_their_own_account(client: httpx.AsyncClient) -> None:
    """Onboarding is refused once an instance exists, so an instance left without an admin can
    never be administered again."""
    headers = await _onboard(client)

    response = await client.request(
        "DELETE",
        "/me",
        headers=headers,
        json={"confirm_email": ADMIN_PAYLOAD["email"], "password": PASSWORD},
    )

    assert response.status_code == 409
    assert await _count(User) == 1


async def test_an_admin_can_leave_once_another_admin_remains(client: httpx.AsyncClient) -> None:
    headers = await _onboard(client)
    await _add_member("second-admin@example.com", role=Role.ADMIN)

    response = await client.request(
        "DELETE",
        "/me",
        headers=headers,
        json={"confirm_email": ADMIN_PAYLOAD["email"], "password": PASSWORD},
    )

    assert response.status_code == 204
    assert await _count(User) == 1


async def test_an_admin_can_delete_another_account(client: httpx.AsyncClient) -> None:
    headers = await _onboard(client)
    member_id = await _add_member("member@example.com")

    response = await client.delete(f"/users/{member_id}", headers=headers)

    assert response.status_code == 204
    assert await _count(User) == 1


async def test_an_admin_deleting_their_own_id_is_sent_to_the_self_route(
    client: httpx.AsyncClient,
) -> None:
    headers = await _onboard(client)
    async with _session()() as session:
        admin = (await session.scalars(select(User).where(User.role == Role.ADMIN))).one()

    response = await client.delete(f"/users/{admin.id}", headers=headers)

    assert response.status_code == 400
    assert await _count(User) == 1


async def test_deleting_an_unknown_account_returns_404(client: httpx.AsyncClient) -> None:
    headers = await _onboard(client)

    assert (await client.delete(f"/users/{uuid4()}", headers=headers)).status_code == 404


async def test_a_member_cannot_delete_somebody_else_s_account(client: httpx.AsyncClient) -> None:
    await _onboard(client)
    member_email = "member@example.com"
    await _add_member(member_email)
    other_id = await _add_member("other@example.com")
    headers = await _login(client, member_email)

    response = await client.delete(f"/users/{other_id}", headers=headers)

    assert response.status_code == 403
    assert await _count(User) == 3
