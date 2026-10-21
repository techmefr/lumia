from collections.abc import AsyncIterator
from datetime import UTC, datetime

import httpx
import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from api.domain.article.models import Article, ArticleShare, Author
from api.domain.feed.models import Feed, SourceType
from api.domain.user.account_service import delete_account
from api.domain.user.models import Instance, Role, User
from api.main import app
from api.technical.auth.jwt import create_access_token
from config.database import get_engine
from config.rate_limit import get_rate_limit_config

ADMIN_PAYLOAD = {
    "email": "admin@example.com",
    "username": "admin",
    "password": "correct-horse-battery-staple",
}

HOSTILE_BODY = (
    "<p>Corps</p><script>alert(1)</script>"
    "<img src='https://example.com/pic.png' alt='photo' onerror='alert(2)'>"
    "<a href='javascript:alert(3)'>piege</a>"
    "<form action='https://evil.test'><input name='password'></form>"
)


@pytest.fixture
async def client(db_schema: None) -> AsyncIterator[httpx.AsyncClient]:
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as async_client:
        yield async_client


def _sessions() -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(get_engine(), expire_on_commit=False)


async def _admin_headers(client: httpx.AsyncClient) -> dict[str, str]:
    response = await client.post("/onboarding/admin", json=ADMIN_PAYLOAD)
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


async def _allow_public_sharing(*, enabled: bool = True) -> None:
    async with _sessions()() as session:
        instance = (await session.scalars(select(Instance))).one()
        instance.public_sharing_enabled = enabled
        await session.commit()


async def _seed_article(
    owner_email: str = "admin@example.com", *, content: str = HOSTILE_BODY
) -> str:
    async with _sessions()() as session:
        owner = (await session.scalars(select(User).where(User.email == owner_email))).one()
        feed = Feed(
            user_id=owner.id,
            source_type=SourceType.MINIFLUX,
            external_feed_id="seeded",
            title="Flux prive du lecteur",
            url="https://example.com/feed",
        )
        author = Author(name="Ada Lovelace")
        session.add_all([feed, author])
        await session.flush()
        article = Article(
            feed_id=feed.id,
            author_id=author.id,
            external_entry_id="e1",
            title="Un ete a Paris",
            url="https://example.com/a",
            content=content,
            image_url="https://example.com/cover.png",
            published_at=datetime(2026, 8, 12, tzinfo=UTC),
        )
        session.add(article)
        await session.commit()
        return str(article.id)


async def _share(client: httpx.AsyncClient, headers: dict[str, str], article_id: str) -> str:
    response = await client.post(f"/articles/{article_id}/share", headers=headers)
    assert response.status_code == 201
    return str(response.json()["token"])


async def _add_member(email: str = "membre@example.com") -> dict[str, str]:
    async with _sessions()() as session:
        instance = (await session.scalars(select(Instance))).one()
        member = User(instance_id=instance.id, email=email, username="membre", role=Role.MEMBER)
        session.add(member)
        await session.commit()
        return {"Authorization": f"Bearer {create_access_token(member.id)}"}


async def test_sharing_is_off_on_a_fresh_instance(client: httpx.AsyncClient) -> None:
    headers = await _admin_headers(client)
    article_id = await _seed_article()

    status = await client.get(f"/articles/{article_id}/share", headers=headers)
    created = await client.post(f"/articles/{article_id}/share", headers=headers)

    assert status.json() == {"enabled": False, "shared": False, "created_at": None}
    assert created.status_code == 403
    assert created.json()["detail"] == "public_sharing_disabled"


async def test_an_admin_turns_public_sharing_on_through_the_settings(
    client: httpx.AsyncClient,
) -> None:
    headers = await _admin_headers(client)

    patched = await client.patch(
        "/instance/settings", headers=headers, json={"public_sharing_enabled": True}
    )

    assert patched.json()["public_sharing_enabled"] is True
    assert (await client.get("/instance/settings", headers=headers)).json()[
        "public_sharing_enabled"
    ] is True


async def test_a_link_opens_the_article_without_an_account(client: httpx.AsyncClient) -> None:
    headers = await _admin_headers(client)
    article_id = await _seed_article()
    await _allow_public_sharing()
    token = await _share(client, headers, article_id)

    response = await client.get(f"/public/articles/{token}")

    assert response.status_code == 200
    body = response.json()
    assert body["title"] == "Un ete a Paris"
    assert body["url"] == "https://example.com/a"
    assert body["author_name"] == "Ada Lovelace"
    assert "Corps" in body["content"]


async def test_the_public_payload_carries_nothing_about_the_reader(
    client: httpx.AsyncClient,
) -> None:
    headers = await _admin_headers(client)
    article_id = await _seed_article()
    await _allow_public_sharing()
    token = await _share(client, headers, article_id)

    response = await client.get(f"/public/articles/{token}")

    assert set(response.json()) == {
        "title",
        "content",
        "url",
        "published_at",
        "author_name",
        "image_url",
        "language",
    }
    for private in (article_id, "Flux prive du lecteur", "admin@example.com"):
        assert private not in response.text


async def test_the_shared_body_is_sanitized_on_the_server(client: httpx.AsyncClient) -> None:
    headers = await _admin_headers(client)
    article_id = await _seed_article()
    await _allow_public_sharing()
    token = await _share(client, headers, article_id)

    content = (await client.get(f"/public/articles/{token}")).json()["content"]

    for active in ("<script", "onerror", "javascript:", "<form", "<input", "alert"):
        assert active not in content
    assert "<img" in content


async def test_the_public_page_is_not_indexable_nor_cacheable(
    client: httpx.AsyncClient,
) -> None:
    headers = await _admin_headers(client)
    article_id = await _seed_article()
    await _allow_public_sharing()
    token = await _share(client, headers, article_id)

    response = await client.get(f"/public/articles/{token}")

    assert "noindex" in response.headers["x-robots-tag"]
    assert response.headers["cache-control"] == "no-store"
    assert response.headers["referrer-policy"] == "no-referrer"


async def test_an_unknown_token_is_a_404_that_is_also_not_indexable(
    client: httpx.AsyncClient,
) -> None:
    await _admin_headers(client)
    await _allow_public_sharing()

    response = await client.get(f"/public/articles/{'x' * 43}")

    assert response.status_code == 404
    assert "noindex" in response.headers["x-robots-tag"]


async def test_a_token_that_cannot_be_one_is_refused_before_any_lookup(
    client: httpx.AsyncClient,
) -> None:
    await _admin_headers(client)

    assert (await client.get("/public/articles/short")).status_code == 422
    assert (await client.get(f"/public/articles/{'x' * 200}")).status_code == 422


async def test_revoking_the_link_closes_it_at_once(client: httpx.AsyncClient) -> None:
    headers = await _admin_headers(client)
    article_id = await _seed_article()
    await _allow_public_sharing()
    token = await _share(client, headers, article_id)

    revoked = await client.delete(f"/articles/{article_id}/share", headers=headers)

    assert revoked.status_code == 204
    assert (await client.get(f"/public/articles/{token}")).status_code == 404
    status = await client.get(f"/articles/{article_id}/share", headers=headers)
    assert status.json()["shared"] is False


async def test_asking_for_a_new_link_retires_the_old_one(client: httpx.AsyncClient) -> None:
    headers = await _admin_headers(client)
    article_id = await _seed_article()
    await _allow_public_sharing()
    first = await _share(client, headers, article_id)

    second = await _share(client, headers, article_id)

    assert first != second
    assert (await client.get(f"/public/articles/{first}")).status_code == 404
    assert (await client.get(f"/public/articles/{second}")).status_code == 200


async def test_the_status_reports_a_live_link(client: httpx.AsyncClient) -> None:
    headers = await _admin_headers(client)
    article_id = await _seed_article()
    await _allow_public_sharing()
    await _share(client, headers, article_id)

    status = (await client.get(f"/articles/{article_id}/share", headers=headers)).json()

    assert status["enabled"] is True
    assert status["shared"] is True
    assert status["created_at"] is not None


async def test_turning_sharing_off_kills_every_existing_link(client: httpx.AsyncClient) -> None:
    headers = await _admin_headers(client)
    article_id = await _seed_article()
    await _allow_public_sharing()
    token = await _share(client, headers, article_id)

    await _allow_public_sharing(enabled=False)

    assert (await client.get(f"/public/articles/{token}")).status_code == 404
    status = await client.get(f"/articles/{article_id}/share", headers=headers)
    assert status.json()["shared"] is False


async def test_only_the_owner_can_manage_the_link(client: httpx.AsyncClient) -> None:
    await _admin_headers(client)
    article_id = await _seed_article()
    await _allow_public_sharing()
    stranger = await _add_member()

    for call in (client.get, client.post, client.delete):
        response = await call(f"/articles/{article_id}/share", headers=stranger)
        assert response.status_code == 404


async def test_managing_a_link_needs_an_account(client: httpx.AsyncClient) -> None:
    await _admin_headers(client)
    article_id = await _seed_article()

    assert (await client.post(f"/articles/{article_id}/share")).status_code == 401


async def test_the_database_keeps_the_hash_and_not_the_token(client: httpx.AsyncClient) -> None:
    headers = await _admin_headers(client)
    article_id = await _seed_article()
    await _allow_public_sharing()
    token = await _share(client, headers, article_id)

    async with _sessions()() as session:
        stored = (await session.scalars(select(ArticleShare))).one()

    assert stored.token_hash != token
    assert token not in stored.token_hash


async def test_walking_the_public_route_ends_in_429(client: httpx.AsyncClient) -> None:
    await _admin_headers(client)
    await _allow_public_sharing()
    allowance = get_rate_limit_config().public_share_max_attempts
    guess = f"/public/articles/{'y' * 43}"

    for _ in range(allowance):
        assert (await client.get(guess)).status_code == 404
    refused = await client.get(guess)

    assert refused.status_code == 429
    assert int(refused.headers["Retry-After"]) > 0


async def test_the_export_lists_the_live_links_without_a_token(client: httpx.AsyncClient) -> None:
    headers = await _admin_headers(client)
    article_id = await _seed_article()
    await _allow_public_sharing()
    token = await _share(client, headers, article_id)

    export = await client.get("/me/export", headers=headers)

    shares = export.json()["shares"]
    assert [share["article_title"] for share in shares] == ["Un ete a Paris"]
    assert shares[0]["article_url"] == "https://example.com/a"
    assert token not in export.text


async def test_the_links_go_with_the_account(client: httpx.AsyncClient) -> None:
    await _admin_headers(client)
    member_headers = await _add_member()
    async with _sessions()() as session:
        member = (await session.scalars(select(User).where(User.role == Role.MEMBER))).one()
        member_id = member.id
    article_id = await _seed_article("membre@example.com")
    await _allow_public_sharing()
    token = await _share(client, member_headers, article_id)

    async with _sessions()() as session:
        await delete_account(session, member_id)
        remaining = await session.scalar(select(func.count()).select_from(ArticleShare))

    assert remaining == 0
    assert (await client.get(f"/public/articles/{token}")).status_code == 404
