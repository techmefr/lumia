from collections.abc import AsyncIterator, Callable
from datetime import UTC, datetime, timedelta
from uuid import UUID

import httpx
import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker

from api.domain.article.models import Article, Lang
from api.domain.audio.models import ArticleAudio
from api.domain.audio.service import store_audio, voice_hash
from api.domain.feed.models import Feed, SourceType
from api.domain.user.models import User
from api.domain.user.providers import get_speech_synthesizer
from api.main import app
from api.technical.net.url_guard import get_url_resolver
from config.database import get_engine
from config.tts import get_tts_config
from worker.technical.speech.base import SynthesizedAudio
from worker.technical.speech.openai_speech import OpenAiSpeechSynthesizer

ADMIN_PAYLOAD = {
    "email": "admin@example.com",
    "username": "admin",
    "password": "correct-horse-battery-staple",
}

Handler = Callable[[httpx.Request], httpx.Response]
PUBLIC = "93.184.216.34"


@pytest.fixture
async def client(db_schema: None, rate_limiter: object) -> AsyncIterator[httpx.AsyncClient]:
    transport = httpx.ASGITransport(app=app)
    app.dependency_overrides[get_url_resolver] = lambda: lambda host: [PUBLIC]
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as async_client:
        yield async_client
    app.dependency_overrides.pop(get_url_resolver, None)
    app.dependency_overrides.pop(get_speech_synthesizer, None)
    get_tts_config.cache_clear()


async def _headers(client: httpx.AsyncClient) -> dict[str, str]:
    response = await client.post("/onboarding/admin", json=ADMIN_PAYLOAD)
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


async def _seed_article(content: str = "<p>The body of the article.</p>") -> str:
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
            content=content,
            original_lang=Lang.EN,
            published_at=datetime(2026, 8, 12, tzinfo=UTC),
        )
        session.add(article)
        await session.commit()
        return str(article.id)


def _use(synthesizer: OpenAiSpeechSynthesizer | None) -> None:
    app.dependency_overrides[get_speech_synthesizer] = lambda: synthesizer


def _speaking(handler: Handler, *, voice: str = "nova") -> OpenAiSpeechSynthesizer:
    return OpenAiSpeechSynthesizer(
        api_key="sk-secret",
        base_url="https://speech.example.test/v1",
        model="tts-1",
        voice=voice,
        transport=httpx.MockTransport(handler),
    )


def _mp3(request: httpx.Request) -> httpx.Response:
    return httpx.Response(200, content=b"ID3-audio")


async def _count_cached() -> int:
    session_factory = async_sessionmaker(get_engine())
    async with session_factory() as session:
        return int(await session.scalar(select(func.count()).select_from(ArticleAudio)) or 0)


async def test_audio_is_generated_returned_as_mpeg_and_kept(client: httpx.AsyncClient) -> None:
    headers = await _headers(client)
    article_id = await _seed_article()
    _use(_speaking(_mp3))

    response = await client.get(f"/articles/{article_id}/audio", headers=headers)

    assert response.status_code == 200
    assert response.headers["content-type"] == "audio/mpeg"
    assert response.content == b"ID3-audio"
    assert await _count_cached() == 1


async def test_audio_is_only_synthesised_once_per_voice(client: httpx.AsyncClient) -> None:
    headers = await _headers(client)
    article_id = await _seed_article()
    calls: list[int] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(1)
        return httpx.Response(200, content=b"first")

    _use(_speaking(handler))
    await client.get(f"/articles/{article_id}/audio", headers=headers)
    again = await client.get(f"/articles/{article_id}/audio", headers=headers)

    assert again.content == b"first"
    assert len(calls) == 1


async def test_a_different_voice_is_synthesised_again(client: httpx.AsyncClient) -> None:
    headers = await _headers(client)
    article_id = await _seed_article()
    _use(_speaking(_mp3, voice="nova"))
    await client.get(f"/articles/{article_id}/audio", headers=headers)
    _use(_speaking(lambda request: httpx.Response(200, content=b"other"), voice="onyx"))

    response = await client.get(f"/articles/{article_id}/audio", headers=headers)

    assert response.content == b"other"
    assert await _count_cached() == 2


async def test_audio_reads_the_title_and_the_text_not_the_markup(
    client: httpx.AsyncClient,
) -> None:
    headers = await _headers(client)
    article_id = await _seed_article()
    sent: list[bytes] = []

    def handler(request: httpx.Request) -> httpx.Response:
        sent.append(request.content)
        return httpx.Response(200, content=b"audio")

    _use(_speaking(handler))
    await client.get(f"/articles/{article_id}/audio", headers=headers)

    assert b"Hello world. The body of the article." in sent[0]
    assert b"<p>" not in sent[0]


async def test_audio_is_unavailable_without_a_provider(client: httpx.AsyncClient) -> None:
    headers = await _headers(client)
    article_id = await _seed_article()
    _use(None)

    response = await client.get(f"/articles/{article_id}/audio", headers=headers)

    assert response.status_code == 503
    assert response.json()["detail"] == "no_tts_provider"


async def test_audio_requires_a_session(client: httpx.AsyncClient) -> None:
    response = await client.get("/articles/00000000-0000-0000-0000-000000000000/audio")

    assert response.status_code == 401


async def test_audio_of_an_unknown_article_is_a_404(client: httpx.AsyncClient) -> None:
    headers = await _headers(client)
    _use(_speaking(_mp3))

    response = await client.get(
        "/articles/00000000-0000-0000-0000-000000000000/audio", headers=headers
    )

    assert response.status_code == 404


async def test_an_article_past_the_length_ceiling_is_refused(
    client: httpx.AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("TTS_MAX_CHARS", "20")
    get_tts_config.cache_clear()
    headers = await _headers(client)
    article_id = await _seed_article()
    _use(_speaking(_mp3))

    response = await client.get(f"/articles/{article_id}/audio", headers=headers)

    assert response.status_code == 413
    assert response.json()["detail"] == "article_too_long"


async def test_a_provider_failure_is_a_502(client: httpx.AsyncClient) -> None:
    headers = await _headers(client)
    article_id = await _seed_article()
    _use(_speaking(lambda request: httpx.Response(500, text="boom")))

    response = await client.get(f"/articles/{article_id}/audio", headers=headers)

    assert response.status_code == 502
    assert response.json()["detail"] == "tts_failed"
    assert await _count_cached() == 0


async def test_an_endpoint_on_a_private_address_is_refused_before_any_request(
    client: httpx.AsyncClient,
) -> None:
    headers = await _headers(client)
    article_id = await _seed_article()
    app.dependency_overrides[get_url_resolver] = lambda: lambda host: ["10.0.0.5"]

    def handler(request: httpx.Request) -> httpx.Response:
        raise AssertionError("nothing may be requested from a blocked endpoint")

    _use(_speaking(handler))

    response = await client.get(f"/articles/{article_id}/audio", headers=headers)

    assert response.status_code == 422
    assert response.json()["detail"] == "tts_endpoint_blocked"


async def test_a_private_endpoint_is_served_when_the_operator_allows_it(
    client: httpx.AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("TTS_ALLOW_PRIVATE_ENDPOINTS", "true")
    get_tts_config.cache_clear()
    headers = await _headers(client)
    article_id = await _seed_article()
    app.dependency_overrides[get_url_resolver] = lambda: lambda host: ["10.0.0.5"]
    _use(_speaking(_mp3))

    response = await client.get(f"/articles/{article_id}/audio", headers=headers)

    assert response.status_code == 200


async def test_generation_is_rate_limited(
    client: httpx.AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("TTS_RATE_LIMIT_MAX_ATTEMPTS", "1")
    get_tts_config.cache_clear()
    headers = await _headers(client)
    first = await _seed_article()
    _use(_speaking(lambda request: httpx.Response(500)))

    await client.get(f"/articles/{first}/audio", headers=headers)
    blocked = await client.get(f"/articles/{first}/audio", headers=headers)

    assert blocked.status_code == 429


async def test_a_cached_reading_is_served_even_when_the_limit_is_spent(
    client: httpx.AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("TTS_RATE_LIMIT_MAX_ATTEMPTS", "1")
    get_tts_config.cache_clear()
    headers = await _headers(client)
    article_id = await _seed_article()
    _use(_speaking(_mp3))

    await client.get(f"/articles/{article_id}/audio", headers=headers)
    again = await client.get(f"/articles/{article_id}/audio", headers=headers)

    assert again.status_code == 200


async def test_the_cache_drops_the_oldest_readings_past_the_account_ceiling(
    client: httpx.AsyncClient,
) -> None:
    await _headers(client)
    session_factory = async_sessionmaker(get_engine(), expire_on_commit=False)
    article_ids = [UUID(await _seed_article_for(n)) for n in range(3)]
    async with session_factory() as session:
        user = (await session.scalars(select(User))).one()
        for article_id in article_ids:
            await store_audio(
                session,
                user_id=user.id,
                article_id=article_id,
                voice=voice_hash("voice"),
                audio=SynthesizedAudio("audio/mpeg", b"x" * 600_000),
                cache_limit_mb=1,
            )
        kept = list(await session.scalars(select(ArticleAudio.article_id)))

    assert kept == [article_ids[2]]


async def _seed_article_for(number: int) -> str:
    session_factory = async_sessionmaker(get_engine(), expire_on_commit=False)
    async with session_factory() as session:
        user = (await session.scalars(select(User))).first()
        assert user is not None
        feed = Feed(
            user_id=user.id,
            source_type=SourceType.MINIFLUX,
            external_feed_id=str(100 + number),
            title="Feed",
            url=f"https://example.com/feed{number}",
        )
        session.add(feed)
        await session.flush()
        article = Article(
            feed_id=feed.id,
            external_entry_id=str(number),
            title=f"Article {number}",
            url=f"https://example.com/a{number}",
            content="<p>Body.</p>",
            original_lang=Lang.EN,
            published_at=datetime(2026, 8, 12, tzinfo=UTC) + timedelta(days=number),
        )
        session.add(article)
        await session.commit()
        return str(article.id)
