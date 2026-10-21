import json

import httpx
import pytest

from worker.technical.speech.base import SpeechApiError
from worker.technical.speech.openai_speech import (
    OpenAiSpeechSynthesizer,
    split_for_speech,
)


def _synthesizer(
    handler: httpx.MockTransport, *, max_audio_bytes: int = 1024
) -> OpenAiSpeechSynthesizer:
    return OpenAiSpeechSynthesizer(
        api_key="sk-secret",
        base_url="https://speech.example.test/v1",
        model="tts-1",
        voice="nova",
        max_audio_bytes=max_audio_bytes,
        transport=handler,
    )


async def test_synthesize_posts_the_text_with_the_configured_voice() -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, content=b"mp3-bytes")

    audio = await _synthesizer(httpx.MockTransport(handler)).synthesize("Bonjour le monde.")

    assert audio.data == b"mp3-bytes"
    assert audio.content_type == "audio/mpeg"
    assert seen[0].url.path == "/v1/audio/speech"
    assert seen[0].headers["authorization"] == "Bearer sk-secret"
    assert json.loads(seen[0].content) == {
        "model": "tts-1",
        "voice": "nova",
        "input": "Bonjour le monde.",
        "response_format": "mp3",
    }


async def test_synthesize_sends_a_long_text_in_pieces_and_joins_the_audio() -> None:
    inputs: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        inputs.append(json.loads(request.content)["input"])
        return httpx.Response(200, content=f"[{len(inputs)}]".encode())

    text = " ".join(["Une phrase assez longue pour remplir la page."] * 200)
    audio = await _synthesizer(httpx.MockTransport(handler)).synthesize(text)

    assert len(inputs) > 1
    assert all(len(piece) <= 4000 for piece in inputs)
    assert audio.data == b"".join(f"[{n}]".encode() for n in range(1, len(inputs) + 1))


async def test_synthesize_raises_a_speech_error_when_the_provider_refuses() -> None:
    transport = httpx.MockTransport(lambda request: httpx.Response(401, text="bad key"))

    with pytest.raises(SpeechApiError):
        await _synthesizer(transport).synthesize("Bonjour.")


async def test_synthesize_refuses_audio_past_the_size_ceiling() -> None:
    transport = httpx.MockTransport(lambda request: httpx.Response(200, content=b"x" * 2048))

    with pytest.raises(SpeechApiError):
        await _synthesizer(transport, max_audio_bytes=1024).synthesize("Bonjour.")


async def test_synthesize_refuses_an_empty_text() -> None:
    transport = httpx.MockTransport(lambda request: httpx.Response(200, content=b"x"))

    with pytest.raises(SpeechApiError):
        await _synthesizer(transport).synthesize("   ")


def test_cache_key_changes_with_the_voice_and_the_model() -> None:
    def key(model: str, voice: str) -> str:
        return OpenAiSpeechSynthesizer(
            api_key="k", base_url="https://a.test/v1", model=model, voice=voice
        ).cache_key

    assert key("tts-1", "nova") != key("tts-1", "alloy")
    assert key("tts-1", "nova") != key("tts-1-hd", "nova")
    assert "sk-" not in key("tts-1", "nova")


def test_split_for_speech_cuts_after_a_sentence_end() -> None:
    pieces = split_for_speech("Premiere phrase. Deuxieme phrase. Troisieme phrase.", limit=30)

    assert pieces == ["Premiere phrase.", "Deuxieme phrase.", "Troisieme phrase."]


def test_split_for_speech_cuts_a_word_less_run_at_the_limit() -> None:
    assert split_for_speech("a" * 25, limit=10) == ["a" * 10, "a" * 10, "a" * 5]
