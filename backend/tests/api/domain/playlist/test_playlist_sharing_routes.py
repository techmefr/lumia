from collections.abc import AsyncIterator
from datetime import UTC, datetime
from uuid import UUID

import httpx
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker

from api.domain.article.models import Article
from api.domain.feed.models import Feed, SourceType
from api.domain.playlist.models import Playlist, PlaylistItem, PlaylistMember
from api.domain.user.models import Instance, Role, User
from api.main import app
from api.technical.auth.jwt import create_access_token
from config.database import get_engine

ADMIN_PAYLOAD = {
    "email": "admin@example.com",
    "username": "admin",
    "password": "correct-horse-battery-staple",
}


@pytest.fixture
async def client(db_schema: None) -> AsyncIterator[httpx.AsyncClient]:
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as async_client:
        yield async_client


def _factory() -> async_sessionmaker:  # type: ignore[type-arg]
    return async_sessionmaker(get_engine(), expire_on_commit=False)


async def _owner_headers(client: httpx.AsyncClient) -> dict[str, str]:
    response = await client.post("/onboarding/admin", json=ADMIN_PAYLOAD)
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


async def _create_user(email: str, *, other_instance: bool = False) -> tuple[UUID, dict[str, str]]:
    async with _factory()() as session:
        owner = (await session.scalars(select(User).order_by(User.created_at))).first()
        assert owner is not None
        instance_id = owner.instance_id
        if other_instance:
            elsewhere = Instance(max_accounts=10, disk_quota_mb=1000)
            session.add(elsewhere)
            await session.flush()
            instance_id = elsewhere.id
        user = User(instance_id=instance_id, email=email, username=email.split("@")[0])
        session.add(user)
        await session.commit()
        return user.id, {"Authorization": f"Bearer {create_access_token(user.id)}"}


async def _seed_article(email: str, external_id: str) -> str:
    async with _factory()() as session:
        user = (await session.scalars(select(User).where(User.email == email))).one()
        feed = Feed(
            user_id=user.id,
            source_type=SourceType.MINIFLUX,
            external_feed_id=external_id,
            title="Feed",
            url=f"https://example.com/{external_id}",
        )
        session.add(feed)
        await session.flush()
        article = Article(
            feed_id=feed.id,
            external_entry_id=external_id,
            title=f"Article {external_id}",
            url=f"https://example.com/a/{external_id}",
            content="mot " * 100,
            published_at=datetime(2026, 8, 12, tzinfo=UTC),
        )
        session.add(article)
        await session.commit()
        return str(article.id)


async def _shared_playlist(
    client: httpx.AsyncClient,
) -> tuple[str, dict[str, dict[str, str]]]:
    """An owner, an editor, a viewer and a stranger, with the playlist shared with the first two."""
    owner = await _owner_headers(client)
    _, editor = await _create_user("editor@example.com")
    _, viewer = await _create_user("viewer@example.com")
    _, stranger = await _create_user("stranger@example.com")
    playlist_id = (await client.post("/playlists", json={"name": "Team"}, headers=owner)).json()[
        "id"
    ]
    for email, role in (("editor@example.com", "editor"), ("viewer@example.com", "viewer")):
        response = await client.put(
            f"/playlists/{playlist_id}/members", json={"email": email, "role": role}, headers=owner
        )
        assert response.status_code == 200
    return playlist_id, {
        "owner": owner,
        "editor": editor,
        "viewer": viewer,
        "stranger": stranger,
    }


async def test_a_shared_playlist_is_listed_with_the_role_of_each_account(
    client: httpx.AsyncClient,
) -> None:
    playlist_id, who = await _shared_playlist(client)

    roles = {}
    for name in ("owner", "editor", "viewer"):
        listed = (await client.get("/playlists", headers=who[name])).json()
        assert [p["id"] for p in listed] == [playlist_id]
        assert listed[0]["owner_name"] == "admin"
        roles[name] = listed[0]["role"]

    assert roles == {"owner": "owner", "editor": "editor", "viewer": "viewer"}
    assert (await client.get("/playlists", headers=who["stranger"])).json() == []


async def test_a_stranger_gets_404_never_403_on_every_route(client: httpx.AsyncClient) -> None:
    playlist_id, who = await _shared_playlist(client)
    stranger = who["stranger"]
    base = f"/playlists/{playlist_id}"
    article_id = "00000000-0000-0000-0000-000000000000"

    responses = [
        await client.get(base, headers=stranger),
        await client.patch(base, json={"name": "X"}, headers=stranger),
        await client.delete(base, headers=stranger),
        await client.post(f"{base}/items", json={"article_id": article_id}, headers=stranger),
        await client.delete(f"{base}/items/{article_id}", headers=stranger),
        await client.put(f"{base}/order", json={"article_ids": []}, headers=stranger),
        await client.get(f"{base}/members", headers=stranger),
        await client.put(
            f"{base}/members",
            json={"email": "viewer@example.com", "role": "editor"},
            headers=stranger,
        ),
    ]

    assert [response.status_code for response in responses] == [404] * len(responses)


async def test_a_viewer_reads_but_cannot_change_anything(client: httpx.AsyncClient) -> None:
    playlist_id, who = await _shared_playlist(client)
    viewer = who["viewer"]
    base = f"/playlists/{playlist_id}"
    article_id = await _seed_article("viewer@example.com", "v1")

    assert (await client.get(base, headers=viewer)).status_code == 200
    assert (await client.get(f"{base}/members", headers=viewer)).status_code == 200
    forbidden = [
        await client.post(f"{base}/items", json={"article_id": article_id}, headers=viewer),
        await client.post(f"{base}/items/bulk", json={"article_ids": [article_id]}, headers=viewer),
        await client.delete(f"{base}/items/{article_id}", headers=viewer),
        await client.put(f"{base}/order", json={"article_ids": []}, headers=viewer),
        await client.patch(base, json={"name": "X"}, headers=viewer),
        await client.delete(base, headers=viewer),
        await client.put(
            f"{base}/members",
            json={"email": "editor@example.com", "role": "viewer"},
            headers=viewer,
        ),
    ]
    assert [response.status_code for response in forbidden] == [403] * len(forbidden)


async def test_an_editor_contributes_and_the_playlist_shows_who_added_what(
    client: httpx.AsyncClient,
) -> None:
    playlist_id, who = await _shared_playlist(client)
    mine = await _seed_article("admin@example.com", "o1")
    theirs = await _seed_article("editor@example.com", "e1")

    await client.post(
        f"/playlists/{playlist_id}/items", json={"article_id": mine}, headers=who["owner"]
    )
    added = await client.post(
        f"/playlists/{playlist_id}/items", json={"article_id": theirs}, headers=who["editor"]
    )
    assert added.status_code == 200

    detail = (await client.get(f"/playlists/{playlist_id}", headers=who["viewer"])).json()
    assert detail["role"] == "viewer"
    assert detail["authorship"] == [
        {"article_id": mine, "added_by": "admin"},
        {"article_id": theirs, "added_by": "editor"},
    ]
    assert [article["id"] for article in detail["articles"]] == [mine, theirs]


async def test_an_editor_cannot_rename_delete_or_manage_members(client: httpx.AsyncClient) -> None:
    playlist_id, who = await _shared_playlist(client)
    editor = who["editor"]
    base = f"/playlists/{playlist_id}"

    assert (await client.patch(base, json={"name": "X"}, headers=editor)).status_code == 403
    assert (await client.delete(base, headers=editor)).status_code == 403
    assert (
        await client.put(
            f"{base}/members",
            json={"email": "viewer@example.com", "role": "editor"},
            headers=editor,
        )
    ).status_code == 403


async def test_an_editor_cannot_add_an_article_that_is_not_theirs(
    client: httpx.AsyncClient,
) -> None:
    playlist_id, who = await _shared_playlist(client)
    owners_article = await _seed_article("admin@example.com", "o1")

    response = await client.post(
        f"/playlists/{playlist_id}/items",
        json={"article_id": owners_article},
        headers=who["editor"],
    )

    assert response.status_code == 404


async def test_sharing_changes_a_role_in_place_and_lists_the_members(
    client: httpx.AsyncClient,
) -> None:
    playlist_id, who = await _shared_playlist(client)

    response = await client.put(
        f"/playlists/{playlist_id}/members",
        json={"email": "viewer@example.com", "role": "editor"},
        headers=who["owner"],
    )

    assert response.json()["owner_name"] == "admin"
    assert {m["username"]: m["role"] for m in response.json()["members"]} == {
        "editor": "editor",
        "viewer": "editor",
    }


async def test_sharing_only_reaches_existing_accounts_of_the_same_instance(
    client: httpx.AsyncClient,
) -> None:
    owner = await _owner_headers(client)
    await _create_user("elsewhere@example.com", other_instance=True)
    playlist_id = (await client.post("/playlists", json={"name": "Team"}, headers=owner)).json()[
        "id"
    ]

    for email in ("nobody@example.com", "elsewhere@example.com"):
        response = await client.put(
            f"/playlists/{playlist_id}/members",
            json={"email": email, "role": "viewer"},
            headers=owner,
        )
        assert response.status_code == 404
        assert response.json()["detail"] == "member_user_not_found"

    async with _factory()() as session:
        assert (await session.scalars(select(PlaylistMember))).all() == []


async def test_the_owner_cannot_be_shared_with_themselves(client: httpx.AsyncClient) -> None:
    owner = await _owner_headers(client)
    playlist_id = (await client.post("/playlists", json={"name": "Team"}, headers=owner)).json()[
        "id"
    ]

    response = await client.put(
        f"/playlists/{playlist_id}/members",
        json={"email": "ADMIN@example.com", "role": "editor"},
        headers=owner,
    )

    assert response.status_code == 422
    assert response.json()["detail"] == "cannot_share_with_owner"


async def test_the_owner_removes_a_member_who_then_loses_access(
    client: httpx.AsyncClient,
) -> None:
    playlist_id, who = await _shared_playlist(client)
    async with _factory()() as session:
        viewer_id = (
            await session.scalars(select(User.id).where(User.email == "viewer@example.com"))
        ).one()

    response = await client.delete(
        f"/playlists/{playlist_id}/members/{viewer_id}", headers=who["owner"]
    )

    assert response.status_code == 204
    assert (await client.get(f"/playlists/{playlist_id}", headers=who["viewer"])).status_code == 404


async def test_a_member_can_leave_but_not_remove_someone_else(client: httpx.AsyncClient) -> None:
    playlist_id, who = await _shared_playlist(client)
    async with _factory()() as session:
        ids = {
            email: user_id
            for email, user_id in (await session.execute(select(User.email, User.id))).all()
        }

    other = await client.delete(
        f"/playlists/{playlist_id}/members/{ids['viewer@example.com']}", headers=who["editor"]
    )
    leaving = await client.delete(
        f"/playlists/{playlist_id}/members/{ids['editor@example.com']}", headers=who["editor"]
    )
    again = await client.delete(
        f"/playlists/{playlist_id}/members/{ids['editor@example.com']}", headers=who["owner"]
    )

    assert (other.status_code, leaving.status_code, again.status_code) == (403, 204, 404)
    assert (await client.get(f"/playlists/{playlist_id}", headers=who["editor"])).status_code == 404


async def test_deleting_a_contributor_account_cleans_their_memberships(
    client: httpx.AsyncClient,
) -> None:
    playlist_id, who = await _shared_playlist(client)
    article_id = await _seed_article("editor@example.com", "e1")
    await client.post(
        f"/playlists/{playlist_id}/items", json={"article_id": article_id}, headers=who["editor"]
    )

    response = await client.request(
        "DELETE", "/me", json={"confirm_email": "editor@example.com"}, headers=who["editor"]
    )
    assert response.status_code == 204, response.text

    async with _factory()() as session:
        members = (await session.scalars(select(PlaylistMember))).all()
        assert [member.role.value for member in members] == ["viewer"]
        assert (await session.scalars(select(PlaylistItem))).all() == []
        assert (await session.scalars(select(Playlist))).one().name == "Team"


async def test_deleting_the_owner_account_removes_the_shared_playlist_and_its_memberships(
    client: httpx.AsyncClient,
) -> None:
    owner = await _owner_headers(client)
    await _create_user("second-admin@example.com")
    async with _factory()() as session:
        other = (
            await session.scalars(select(User).where(User.email == "second-admin@example.com"))
        ).one()
        other.role = Role.ADMIN
        await session.commit()
    _, viewer = await _create_user("viewer@example.com")
    playlist_id = (await client.post("/playlists", json={"name": "Team"}, headers=owner)).json()[
        "id"
    ]
    await client.put(
        f"/playlists/{playlist_id}/members",
        json={"email": "viewer@example.com", "role": "viewer"},
        headers=owner,
    )

    response = await client.request(
        "DELETE",
        "/me",
        json={"confirm_email": ADMIN_PAYLOAD["email"], "password": ADMIN_PAYLOAD["password"]},
        headers=owner,
    )
    assert response.status_code == 204, response.text

    async with _factory()() as session:
        assert (await session.scalars(select(PlaylistMember))).all() == []
        assert (await session.scalars(select(Playlist))).all() == []
    assert (await client.get(f"/playlists/{playlist_id}", headers=viewer)).status_code == 404
