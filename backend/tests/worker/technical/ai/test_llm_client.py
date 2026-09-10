import logging

import httpx
import pytest

from worker.technical.ai.llm_client import (
    LlmApiError,
    OpenAiCompatibleChatClient,
    resolve_base_url,
    resolve_model,
)


def _summarizer(handler: object) -> OpenAiCompatibleChatClient:
    return OpenAiCompatibleChatClient(
        api_key="sk-test",
        base_url="http://provider.test/v1",
        model="test-model",
        transport=httpx.MockTransport(handler),  # type: ignore[arg-type]
    )


async def test_summarize_returns_the_first_choice_content() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["Authorization"] == "Bearer sk-test"
        assert request.url.path == "/v1/chat/completions"
        return httpx.Response(200, json={"choices": [{"message": {"content": "  Un résumé.  "}}]})

    assert await _summarizer(handler).summarize("texte") == "Un résumé."


async def test_summarize_sends_the_configured_model() -> None:
    seen: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        import json

        seen.update(json.loads(request.content))
        return httpx.Response(200, json={"choices": [{"message": {"content": "ok"}}]})

    await _summarizer(handler).summarize("texte")
    assert seen["model"] == "test-model"


async def test_summarize_truncates_a_very_long_article() -> None:
    seen: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        import json

        seen.update(json.loads(request.content))
        return httpx.Response(200, json={"choices": [{"message": {"content": "ok"}}]})

    await _summarizer(handler).summarize("a" * 20_000)
    assert len(seen["messages"][1]["content"]) == 12_000  # type: ignore[index]


async def test_summarize_raises_on_an_error_status() -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, text="invalid api key")

    with pytest.raises(LlmApiError):
        await _summarizer(handler).summarize("texte")


async def test_summarize_raises_when_no_choice_comes_back() -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"choices": []})

    with pytest.raises(LlmApiError):
        await _summarizer(handler).summarize("texte")


def test_resolve_base_url_knows_the_hosted_providers() -> None:
    assert resolve_base_url("mistral", None) == "https://api.mistral.ai/v1"
    assert resolve_base_url("openai", None) == "https://api.openai.com/v1"


def test_resolve_base_url_uses_the_endpoint_for_a_custom_provider() -> None:
    assert resolve_base_url("custom", "http://voxtral.local/v1/") == "http://voxtral.local/v1"


def test_resolve_base_url_returns_none_for_a_custom_provider_without_an_endpoint() -> None:
    assert resolve_base_url("custom", None) is None


def test_resolve_model_prefers_the_explicit_model() -> None:
    assert resolve_model("mistral", "mistral-large-latest") == "mistral-large-latest"


def test_resolve_model_falls_back_to_the_provider_default() -> None:
    assert resolve_model("openai", None) == "gpt-4o-mini"


def test_resolve_model_has_no_default_for_a_custom_provider() -> None:
    assert resolve_model("custom", None) is None


async def test_summarize_logs_the_url_and_the_status_of_a_rejected_call(
    caplog: pytest.LogCaptureFixture,
) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(429, text="rate limited")

    summarizer = OpenAiCompatibleChatClient(
        api_key="key",
        base_url="https://provider.test/v1",
        model="small",
        transport=httpx.MockTransport(handler),
    )
    with caplog.at_level(logging.WARNING), pytest.raises(LlmApiError):
        await summarizer.summarize("Un texte a resumer")

    record = caplog.records[-1]
    assert record.service == "openai-compatible"  # type: ignore[attr-defined]
    assert record.status_code == 429  # type: ignore[attr-defined]
    assert record.url == "https://provider.test/v1/chat/completions"  # type: ignore[attr-defined]
