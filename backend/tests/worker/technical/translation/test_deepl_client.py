import logging

import httpx
import pytest

from worker.technical.translation.deepl_client import DeeplApiError, DeeplTranslator


async def test_translate_returns_the_translated_text() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/v2/translate"
        assert request.headers["authorization"] == "DeepL-Auth-Key test-deepl-key"
        return httpx.Response(200, json={"translations": [{"text": "Bonjour le monde"}]})

    translator = DeeplTranslator(transport=httpx.MockTransport(handler))
    translated = await translator.translate("Hello world", target_lang="fr")
    assert translated == "Bonjour le monde"


async def test_translate_sends_the_regional_code_deepl_expects() -> None:
    """Portuguese and English are only accepted as a regional variant, `PT` alone is rejected."""

    def handler(request: httpx.Request) -> httpx.Response:
        assert b'"target_lang":"PT-PT"' in request.content
        return httpx.Response(200, json={"translations": [{"text": "Ola mundo"}]})

    translator = DeeplTranslator(transport=httpx.MockTransport(handler))
    assert await translator.translate("Hello world", target_lang="pt") == "Ola mundo"


async def test_supports_reports_the_languages_deepl_has() -> None:
    translator = DeeplTranslator()
    assert translator.supports("de")
    assert not translator.supports("mg")


async def test_translate_refuses_a_language_deepl_does_not_have() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise AssertionError("no request should be sent for an unsupported language")

    translator = DeeplTranslator(transport=httpx.MockTransport(handler))
    with pytest.raises(DeeplApiError):
        await translator.translate("Hello world", target_lang="mg")


async def test_translate_raises_on_an_error_response() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(456, text="quota exceeded")

    translator = DeeplTranslator(transport=httpx.MockTransport(handler))
    with pytest.raises(DeeplApiError):
        await translator.translate("Hello world", target_lang="fr")


async def test_translate_logs_the_url_and_the_status_of_a_rejected_call(
    caplog: pytest.LogCaptureFixture,
) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(456, text="quota exceeded")

    translator = DeeplTranslator(transport=httpx.MockTransport(handler))
    with caplog.at_level(logging.WARNING), pytest.raises(DeeplApiError):
        await translator.translate("Hello world", target_lang="fr")

    record = caplog.records[-1]
    assert record.service == "deepl"  # type: ignore[attr-defined]
    assert record.status_code == 456  # type: ignore[attr-defined]
    assert record.url.endswith("/v2/translate")  # type: ignore[attr-defined]
