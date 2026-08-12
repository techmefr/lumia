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


async def test_translate_raises_on_an_error_response() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(456, text="quota exceeded")

    translator = DeeplTranslator(transport=httpx.MockTransport(handler))
    with pytest.raises(DeeplApiError):
        await translator.translate("Hello world", target_lang="fr")
