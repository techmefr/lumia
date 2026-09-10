from collections.abc import AsyncIterator, Callable
from datetime import UTC, datetime
from uuid import uuid4

import httpx
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker

from api.domain.article.models import Article, Lang
from api.domain.feed.models import Feed, SourceType
from api.domain.user.models import User
from api.domain.user.providers import get_translator
from api.main import app
from config.database import get_engine
from worker.technical.ai.llm_client import OpenAiCompatibleChatClient
from worker.technical.translation.base import Translator
from worker.technical.translation.deepl_client import DeeplTranslator
from worker.technical.translation.llm_translator import LlmTranslator

ADMIN_PAYLOAD = {
    "email": "admin@example.com",
    "username": "admin",
    "password": "correct-horse-battery-staple",
}

Handler = Callable[[httpx.Request], httpx.Response]


@pytest.fixture
async def client(db_schema: None) -> AsyncIterator[httpx.AsyncClient]:
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as async_client:
        yield async_client
    app.dependency_overrides.clear()


async def _headers(client: httpx.AsyncClient) -> dict[str, str]:
    response = await client.post("/onboarding/admin", json=ADMIN_PAYLOAD)
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


async def _seed_article() -> str:
    session_factory = async_sessionmaker(get_engine(), expire_on_commit=False)
    async with session_factory() as session:
        user = (await session.scalars(select(User))).first()
        assert user is not None
        feed = Feed(
            user_id=user.id,
            source_type=SourceType.MINIFLUX,
            external_feed_id="10",
            title="Feed",
            url="https://example.com/feed",
        )
        session.add(feed)
        await session.flush()
        article = Article(
            feed_id=feed.id,
            external_entry_id="1",
            title="Hello world",
            url="https://example.com/a",
            content="<p>The body of the article.</p>",
            original_lang=Lang.EN,
            published_at=datetime(2026, 8, 12, tzinfo=UTC),
        )
        session.add(article)
        await session.commit()
        return str(article.id)


def _use(translator: Translator | None) -> None:
    app.dependency_overrides[get_translator] = lambda: translator


def _deepl(handler: Handler) -> DeeplTranslator:
    """The real DeepL client, faked only at the HTTP transport."""
    return DeeplTranslator(api_key="deepl-secret", transport=httpx.MockTransport(handler))


def _llm(handler: Handler) -> LlmTranslator:
    return LlmTranslator(
        chat_client=OpenAiCompatibleChatClient(
            api_key="sk-secret",
            base_url="https://api.mistral.ai/v1",
            model="mistral-small-latest",
            transport=httpx.MockTransport(handler),
        )
    )


def _deepl_answering(*texts: str) -> DeeplTranslator:
    answers = iter(texts)
    return _deepl(
        lambda request: httpx.Response(200, json={"translations": [{"text": next(answers)}]})
    )


async def test_translate_returns_the_title_and_the_body(client: httpx.AsyncClient) -> None:
    headers = await _headers(client)
    article_id = await _seed_article()
    _use(_deepl_answering("Bonjour le monde", "Le corps de l'article."))

    response = await client.post(
        f"/articles/{article_id}/translate", json={"target_lang": "fr"}, headers=headers
    )
    assert response.status_code == 200
    assert response.json() == {
        "target_lang": "fr",
        "title": "Bonjour le monde",
        "content": "Le corps de l'article.",
    }


async def test_translate_sends_the_body_as_text_not_as_markup(client: httpx.AsyncClient) -> None:
    headers = await _headers(client)
    article_id = await _seed_article()
    sent: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        sent.append(request.content.decode())
        return httpx.Response(200, json={"translations": [{"text": "Traduit"}]})

    _use(_deepl(handler))
    await client.post(
        f"/articles/{article_id}/translate", json={"target_lang": "fr"}, headers=headers
    )
    assert sent
    assert not any("<p>" in body for body in sent)


async def test_translate_works_through_the_accounts_own_model(client: httpx.AsyncClient) -> None:
    """Malagasy has no DeepL entry, so this only answers through the LLM provider."""
    headers = await _headers(client)
    article_id = await _seed_article()
    _use(
        _llm(
            lambda request: httpx.Response(
                200, json={"choices": [{"message": {"content": "Traduit"}}]}
            )
        )
    )

    response = await client.post(
        f"/articles/{article_id}/translate", json={"target_lang": "mg"}, headers=headers
    )
    assert response.status_code == 200
    assert response.json()["content"] == "Traduit"


async def test_translate_leaves_the_stored_article_alone(client: httpx.AsyncClient) -> None:
    headers = await _headers(client)
    article_id = await _seed_article()
    _use(_deepl_answering("Bonjour le monde", "Traduit"))

    await client.post(
        f"/articles/{article_id}/translate", json={"target_lang": "fr"}, headers=headers
    )
    detail = await client.get(f"/articles/{article_id}", headers=headers)
    assert detail.json()["title"] == "Hello world"


async def test_translate_is_unavailable_without_any_configured_provider(
    client: httpx.AsyncClient,
) -> None:
    headers = await _headers(client)
    article_id = await _seed_article()
    _use(None)

    response = await client.post(
        f"/articles/{article_id}/translate", json={"target_lang": "fr"}, headers=headers
    )
    assert response.status_code == 503
    assert response.json()["detail"] == "no_translation_provider"


async def test_translate_is_unavailable_for_a_language_the_provider_misses(
    client: httpx.AsyncClient,
) -> None:
    headers = await _headers(client)
    article_id = await _seed_article()

    def handler(request: httpx.Request) -> httpx.Response:
        raise AssertionError("no request should be sent for an unsupported language")

    _use(_deepl(handler))
    response = await client.post(
        f"/articles/{article_id}/translate", json={"target_lang": "mg"}, headers=headers
    )
    assert response.status_code == 503
    assert response.json()["detail"] == "language_not_supported"


async def test_translate_hides_what_the_provider_said_when_it_fails(
    client: httpx.AsyncClient,
) -> None:
    """The provider's own error text can echo the account's key back."""
    headers = await _headers(client)
    article_id = await _seed_article()
    _use(_deepl(lambda request: httpx.Response(403, text="invalid key deepl-secret")))

    response = await client.post(
        f"/articles/{article_id}/translate", json={"target_lang": "fr"}, headers=headers
    )
    assert response.status_code == 502
    assert response.json()["detail"] == "translation_failed"
    assert "deepl-secret" not in response.text


async def test_translate_refuses_a_language_the_app_does_not_offer(
    client: httpx.AsyncClient,
) -> None:
    headers = await _headers(client)
    article_id = await _seed_article()
    _use(_deepl_answering("x", "x"))

    response = await client.post(
        f"/articles/{article_id}/translate", json={"target_lang": "nl"}, headers=headers
    )
    assert response.status_code == 422


async def test_translate_does_not_reach_an_article_the_reader_does_not_own(
    client: httpx.AsyncClient,
) -> None:
    headers = await _headers(client)
    _use(_deepl_answering("x", "x"))

    response = await client.post(
        f"/articles/{uuid4()}/translate", json={"target_lang": "fr"}, headers=headers
    )
    assert response.status_code == 404
