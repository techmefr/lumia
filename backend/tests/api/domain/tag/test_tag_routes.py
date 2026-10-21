from collections.abc import AsyncIterator, Iterator
from datetime import UTC, datetime

import httpx
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker

from api.domain.article.models import Article, ArticleKeyword, Keyword, Lang
from api.domain.feed.models import Feed, SourceType
from api.domain.user.models import User
from api.domain.user.providers import get_chat_client
from api.main import app
from api.technical.auth.jwt import create_access_token
from config.database import get_engine
from worker.technical.ai.base import LlmApiError

ADMIN_PAYLOAD = {
    "email": "admin@example.com",
    "username": "admin",
    "password": "correct-horse-battery-staple",
}
UNKNOWN_ID = "00000000-0000-0000-0000-000000000000"


class ScriptedChat:
    def __init__(self, answer: str = "", error: Exception | None = None) -> None:
        self.answer = answer
        self.error = error
        self.prompts: list[str] = []

    async def complete(self, *, system: str, user: str) -> str:
        self.prompts.append(user)
        if self.error is not None:
            raise self.error
        return self.answer

    async def summarize(self, text: str) -> str:
        return text


@pytest.fixture
async def client(db_schema: None) -> AsyncIterator[httpx.AsyncClient]:
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as async_client:
        yield async_client


@pytest.fixture(autouse=True)
def no_ai_by_default() -> Iterator[None]:
    app.dependency_overrides[get_chat_client] = lambda: None
    yield
    app.dependency_overrides.pop(get_chat_client, None)


async def _headers(client: httpx.AsyncClient) -> dict[str, str]:
    response = await client.post("/onboarding/admin", json=ADMIN_PAYLOAD)
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


async def _other_headers() -> dict[str, str]:
    async with async_sessionmaker(get_engine(), expire_on_commit=False)() as session:
        user = (await session.scalars(select(User))).one()
        other = User(instance_id=user.instance_id, email="other@example.com", username="other")
        session.add(other)
        await session.commit()
        return {"Authorization": f"Bearer {create_access_token(other.id)}"}


async def _seed_articles(count: int = 2, *, keywords: tuple[str, ...] = ()) -> list[str]:
    async with async_sessionmaker(get_engine(), expire_on_commit=False)() as session:
        user = (await session.scalars(select(User))).one()
        feed = Feed(
            user_id=user.id,
            source_type=SourceType.MINIFLUX,
            external_feed_id="1",
            title="Feed",
            url="https://example.com/feed",
        )
        session.add(feed)
        await session.flush()
        articles = [
            Article(
                feed_id=feed.id,
                external_entry_id=str(index),
                title=f"Article {index}",
                url=f"https://example.com/{index}",
                content="<p>Une recette de cuisine.</p>",
                published_at=datetime(2026, 8, 12, tzinfo=UTC),
            )
            for index in range(count)
        ]
        session.add_all(articles)
        await session.flush()
        for rank, term in enumerate(keywords):
            keyword = Keyword(term=term, lang=Lang.FR)
            session.add(keyword)
            await session.flush()
            session.add(
                ArticleKeyword(article_id=articles[0].id, keyword_id=keyword.id, weight=10.0 - rank)
            )
        await session.commit()
        return [str(article.id) for article in articles]


async def _tag(
    client: httpx.AsyncClient, headers: dict[str, str], article_id: str, name: str
) -> list[dict[str, str]]:
    response = await client.post(
        f"/articles/{article_id}/tags", json={"name": name}, headers=headers
    )
    assert response.status_code == 200
    return list(response.json())


async def test_create_list_rename_and_delete_a_tag(client: httpx.AsyncClient) -> None:
    headers = await _headers(client)

    created = await client.post("/tags", json={"name": "  Cuisine  "}, headers=headers)
    assert created.status_code == 201
    assert created.json()["name"] == "Cuisine"
    assert created.json()["article_count"] == 0
    tag_id = created.json()["id"]

    renamed = await client.patch(f"/tags/{tag_id}", json={"name": "Recettes"}, headers=headers)
    assert renamed.json()["name"] == "Recettes"
    assert [tag["name"] for tag in (await client.get("/tags", headers=headers)).json()] == [
        "Recettes"
    ]

    assert (await client.delete(f"/tags/{tag_id}", headers=headers)).status_code == 204
    assert (await client.get("/tags", headers=headers)).json() == []


async def test_a_tag_name_is_unique_whatever_its_case(client: httpx.AsyncClient) -> None:
    headers = await _headers(client)
    await client.post("/tags", json={"name": "Cuisine"}, headers=headers)

    duplicate = await client.post("/tags", json={"name": "cuisine"}, headers=headers)

    assert duplicate.status_code == 409
    assert duplicate.json()["detail"] == "tag_name_taken"


async def test_renaming_onto_another_tag_is_refused_but_recasing_itself_is_not(
    client: httpx.AsyncClient,
) -> None:
    headers = await _headers(client)
    first = (await client.post("/tags", json={"name": "Cuisine"}, headers=headers)).json()
    await client.post("/tags", json={"name": "Voyage"}, headers=headers)

    clash = await client.patch(f"/tags/{first['id']}", json={"name": "voyage"}, headers=headers)
    recase = await client.patch(f"/tags/{first['id']}", json={"name": "CUISINE"}, headers=headers)

    assert clash.status_code == 409
    assert recase.json()["name"] == "CUISINE"


@pytest.mark.parametrize("name", ["", "   ", "x" * 41])
async def test_an_empty_or_oversized_name_is_rejected(client: httpx.AsyncClient, name: str) -> None:
    headers = await _headers(client)

    response = await client.post("/tags", json={"name": name}, headers=headers)

    assert response.status_code == 422


async def test_unknown_tag_is_404_for_rename_and_delete(client: httpx.AsyncClient) -> None:
    headers = await _headers(client)

    renamed = await client.patch(f"/tags/{UNKNOWN_ID}", json={"name": "x"}, headers=headers)
    deleted = await client.delete(f"/tags/{UNKNOWN_ID}", headers=headers)

    assert renamed.status_code == 404
    assert deleted.status_code == 404


async def test_tagging_creates_the_tag_and_is_idempotent(client: httpx.AsyncClient) -> None:
    headers = await _headers(client)
    article_id = (await _seed_articles(1))[0]

    first = await _tag(client, headers, article_id, "Cuisine")
    again = await _tag(client, headers, article_id, "cuisine")

    assert [tag["name"] for tag in first] == ["Cuisine"]
    assert again == first
    listed = (await client.get("/tags", headers=headers)).json()
    assert [(tag["name"], tag["article_count"]) for tag in listed] == [("Cuisine", 1)]


async def test_untagging_keeps_the_tag_and_updates_the_count(client: httpx.AsyncClient) -> None:
    headers = await _headers(client)
    article_id = (await _seed_articles(1))[0]
    tag = (await _tag(client, headers, article_id, "Cuisine"))[0]

    remaining = await client.delete(f"/articles/{article_id}/tags/{tag['id']}", headers=headers)

    assert remaining.json() == []
    listed = (await client.get("/tags", headers=headers)).json()
    assert [(item["name"], item["article_count"]) for item in listed] == [("Cuisine", 0)]


async def test_untagging_with_an_unknown_tag_is_404(client: httpx.AsyncClient) -> None:
    headers = await _headers(client)
    article_id = (await _seed_articles(1))[0]

    response = await client.delete(f"/articles/{article_id}/tags/{UNKNOWN_ID}", headers=headers)

    assert response.status_code == 404


async def test_deleting_a_tag_untags_its_articles(client: httpx.AsyncClient) -> None:
    headers = await _headers(client)
    article_id = (await _seed_articles(1))[0]
    tag = (await _tag(client, headers, article_id, "Cuisine"))[0]

    await client.delete(f"/tags/{tag['id']}", headers=headers)

    detail = (await client.get(f"/articles/{article_id}", headers=headers)).json()
    assert detail["tags"] == []


async def test_the_article_detail_and_list_carry_their_tags(client: httpx.AsyncClient) -> None:
    headers = await _headers(client)
    first, second = await _seed_articles(2)
    await _tag(client, headers, first, "Voyage")
    await _tag(client, headers, first, "cuisine")

    detail = (await client.get(f"/articles/{first}", headers=headers)).json()
    listed = {
        item["id"]: item["tags"] for item in (await client.get("/articles", headers=headers)).json()
    }

    assert [tag["name"] for tag in detail["tags"]] == ["cuisine", "Voyage"]
    assert [tag["name"] for tag in listed[first]] == ["cuisine", "Voyage"]
    assert listed[second] == []


async def test_filtering_the_list_by_tag(client: httpx.AsyncClient) -> None:
    headers = await _headers(client)
    first, _ = await _seed_articles(2)
    tag = (await _tag(client, headers, first, "Cuisine"))[0]

    response = await client.get("/articles", params={"tag_id": tag["id"]}, headers=headers)

    assert [item["id"] for item in response.json()] == [first]


async def test_the_tag_filter_combines_with_the_other_filters(client: httpx.AsyncClient) -> None:
    headers = await _headers(client)
    first, _ = await _seed_articles(2)
    tag = (await _tag(client, headers, first, "Cuisine"))[0]

    matching = await client.get(
        "/articles", params={"tag_id": tag["id"], "unread_only": "true"}, headers=headers
    )
    excluded = await client.get(
        "/articles", params={"tag_id": tag["id"], "q": "introuvable"}, headers=headers
    )

    assert [item["id"] for item in matching.json()] == [first]
    assert excluded.json() == []


async def test_another_readers_tags_are_invisible_and_unusable(
    client: httpx.AsyncClient,
) -> None:
    headers = await _headers(client)
    article_id = (await _seed_articles(1))[0]
    mine = (await _tag(client, headers, article_id, "Cuisine"))[0]
    other = await _other_headers()

    assert (await client.get("/tags", headers=other)).json() == []
    assert (
        await client.patch(f"/tags/{mine['id']}", json={"name": "x"}, headers=other)
    ).status_code == 404
    assert (await client.delete(f"/tags/{mine['id']}", headers=other)).status_code == 404
    assert (
        await client.post(f"/articles/{article_id}/tags", json={"name": "x"}, headers=other)
    ).status_code == 404
    assert (
        await client.delete(f"/articles/{article_id}/tags/{mine['id']}", headers=other)
    ).status_code == 404
    assert (
        await client.get(f"/articles/{article_id}/tag-suggestions", headers=other)
    ).status_code == 404
    assert (
        await client.post(f"/articles/{article_id}/tag-suggestions/ai", headers=other)
    ).status_code == 404
    assert (
        await client.get("/articles", params={"tag_id": mine["id"]}, headers=other)
    ).json() == []


async def test_two_readers_may_use_the_same_tag_name(client: httpx.AsyncClient) -> None:
    headers = await _headers(client)
    await client.post("/tags", json={"name": "Cuisine"}, headers=headers)
    other = await _other_headers()

    response = await client.post("/tags", json={"name": "Cuisine"}, headers=other)

    assert response.status_code == 201


async def test_suggestions_offer_keywords_then_the_most_used_tags(
    client: httpx.AsyncClient,
) -> None:
    headers = await _headers(client)
    first, second = await _seed_articles(2, keywords=("recette", "four", "sucre", "farine"))
    await _tag(client, headers, second, "Voyage")
    await _tag(client, headers, second, "Cuisine")
    await _tag(client, headers, (await _seed_more())[0], "Voyage")

    response = await client.get(f"/articles/{first}/tag-suggestions", headers=headers)

    assert [(item["name"], item["source"]) for item in response.json()] == [
        ("recette", "keyword"),
        ("four", "keyword"),
        ("sucre", "keyword"),
        ("Voyage", "used"),
        ("Cuisine", "used"),
    ]


async def _seed_more() -> list[str]:
    async with async_sessionmaker(get_engine(), expire_on_commit=False)() as session:
        feed = (await session.scalars(select(Feed))).one()
        article = Article(
            feed_id=feed.id,
            external_entry_id="extra",
            title="Extra",
            url="https://example.com/extra",
            content="<p>x</p>",
            published_at=datetime(2026, 8, 12, tzinfo=UTC),
        )
        session.add(article)
        await session.commit()
        return [str(article.id)]


async def test_suggestions_skip_what_the_article_already_carries(
    client: httpx.AsyncClient,
) -> None:
    headers = await _headers(client)
    first, _ = await _seed_articles(2, keywords=("recette", "four"))
    await _tag(client, headers, first, "Recette")

    response = await client.get(f"/articles/{first}/tag-suggestions", headers=headers)

    assert [item["name"] for item in response.json()] == ["four"]


async def test_suggesting_never_tags_anything(client: httpx.AsyncClient) -> None:
    headers = await _headers(client)
    first, _ = await _seed_articles(2, keywords=("recette",))

    await client.get(f"/articles/{first}/tag-suggestions", headers=headers)

    assert (await client.get("/tags", headers=headers)).json() == []


async def test_ai_suggestions_come_from_the_account_model(client: httpx.AsyncClient) -> None:
    headers = await _headers(client)
    first, _ = await _seed_articles(2)
    await _tag(client, headers, first, "Cuisine")
    chat = ScriptedChat('- Gastronomie\n2. cuisine\n\n"Pâtisserie"\n')
    app.dependency_overrides[get_chat_client] = lambda: chat

    response = await client.post(f"/articles/{first}/tag-suggestions/ai", headers=headers)

    assert [(item["name"], item["source"]) for item in response.json()] == [
        ("Gastronomie", "ai"),
        ("Pâtisserie", "ai"),
    ]
    assert "Article 0" in chat.prompts[0]
    assert "Une recette de cuisine." in chat.prompts[0]
    assert (await client.get("/tags", headers=headers)).json()[0]["article_count"] == 1


async def test_ai_suggestions_are_unavailable_without_a_provider(
    client: httpx.AsyncClient,
) -> None:
    headers = await _headers(client)
    first = (await _seed_articles(1))[0]

    response = await client.post(f"/articles/{first}/tag-suggestions/ai", headers=headers)

    assert response.status_code == 503
    assert response.json()["detail"] == "no_ai_provider"


async def test_a_failing_provider_is_a_bad_gateway(client: httpx.AsyncClient) -> None:
    headers = await _headers(client)
    first = (await _seed_articles(1))[0]
    app.dependency_overrides[get_chat_client] = lambda: ScriptedChat(
        error=LlmApiError("boom with a secret")
    )

    response = await client.post(f"/articles/{first}/tag-suggestions/ai", headers=headers)

    assert response.status_code == 502
    assert response.json()["detail"] == "ai_suggestion_failed"
