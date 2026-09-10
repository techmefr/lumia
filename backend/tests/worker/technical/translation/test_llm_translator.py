import httpx
import pytest

from worker.technical.ai.llm_client import OpenAiCompatibleChatClient
from worker.technical.translation.base import TranslationApiError
from worker.technical.translation.llm_translator import (
    MAX_TRANSLATABLE_CHARS,
    LlmTranslationError,
    LlmTranslator,
)


def _translator(handler: object) -> LlmTranslator:
    chat_client = OpenAiCompatibleChatClient(
        api_key="sk-secret",
        base_url="https://api.mistral.ai/v1",
        model="mistral-small-latest",
        transport=httpx.MockTransport(handler),  # type: ignore[arg-type]
    )
    return LlmTranslator(chat_client=chat_client)


async def test_translate_returns_what_the_model_answered() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"choices": [{"message": {"content": "Bonjour le monde"}}]})

    assert await _translator(handler).translate("Hello world", target_lang="fr") == (
        "Bonjour le monde"
    )


async def test_translate_names_the_target_language_in_the_prompt() -> None:
    """A bare two-letter code is ambiguous prose to a chat model, the language name is not."""

    def handler(request: httpx.Request) -> httpx.Response:
        assert "malgache" in request.content.decode()
        return httpx.Response(200, json={"choices": [{"message": {"content": "Salama tontolo"}}]})

    assert await _translator(handler).translate("Hello world", target_lang="mg")


async def test_translate_sends_the_whole_text_rather_than_the_opening() -> None:
    text = "Une phrase. " * 200

    def handler(request: httpx.Request) -> httpx.Response:
        assert text in request.content.decode()
        return httpx.Response(200, json={"choices": [{"message": {"content": "Traduit"}}]})

    assert await _translator(handler).translate(text, target_lang="en") == "Traduit"


async def test_supports_covers_every_reading_language_deepl_misses() -> None:
    translator = _translator(lambda request: httpx.Response(200, json={}))
    assert translator.supports("mg")
    assert translator.supports("ZH")
    assert not translator.supports("nl")


async def test_translate_refuses_a_language_it_has_no_name_for() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise AssertionError("no request should be sent for an unknown language")

    with pytest.raises(LlmTranslationError):
        await _translator(handler).translate("Hello world", target_lang="nl")


async def test_translate_refuses_a_text_too_long_to_come_back_whole() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise AssertionError("no request should be sent for an oversized text")

    with pytest.raises(LlmTranslationError):
        await _translator(handler).translate("a" * (MAX_TRANSLATABLE_CHARS + 1), target_lang="fr")


async def test_translate_reports_a_provider_error_as_a_translation_failure() -> None:
    """So a caller degrades without having to know which provider it was handed."""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(429, text="rate limited")

    with pytest.raises(LlmTranslationError):
        await _translator(handler).translate("Hello world", target_lang="fr")


async def test_translate_reports_an_unreachable_provider_as_a_translation_failure() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("provider unreachable")

    with pytest.raises(LlmTranslationError):
        await _translator(handler).translate("Hello world", target_lang="fr")


async def test_translate_refuses_an_empty_answer_rather_than_blanking_the_article() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"choices": [{"message": {"content": "   "}}]})

    with pytest.raises(LlmTranslationError):
        await _translator(handler).translate("Hello world", target_lang="fr")


async def test_a_failure_is_catchable_as_the_shared_translation_error() -> None:
    """enrich_article and the endpoint both catch the shared type, never a provider's own."""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, text="boom")

    with pytest.raises(TranslationApiError):
        await _translator(handler).translate("Hello world", target_lang="fr")
