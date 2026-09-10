import json
import logging

import httpx
import pytest

from worker.technical.ai.anthropic_client import API_VERSION, AnthropicChatClient
from worker.technical.ai.base import LlmApiError


def _summarizer(handler: object) -> AnthropicChatClient:
    return AnthropicChatClient(
        api_key="sk-ant-test",
        model="claude-test",
        transport=httpx.MockTransport(handler),  # type: ignore[arg-type]
    )


async def test_summarize_returns_the_joined_text_blocks() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/v1/messages"
        return httpx.Response(
            200,
            json={
                "content": [{"type": "text", "text": " Un "}, {"type": "text", "text": "résumé. "}]
            },
        )

    assert await _summarizer(handler).summarize("texte") == "Un résumé."


async def test_summarize_authenticates_with_the_api_key_header_and_the_version() -> None:
    seen: dict[str, str] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["key"] = request.headers["x-api-key"]
        seen["version"] = request.headers["anthropic-version"]
        return httpx.Response(200, json={"content": [{"type": "text", "text": "ok"}]})

    await _summarizer(handler).summarize("texte")
    assert seen == {"key": "sk-ant-test", "version": API_VERSION}


async def test_summarize_sends_the_prompt_as_a_top_level_system_field() -> None:
    seen: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen.update(json.loads(request.content))
        return httpx.Response(200, json={"content": [{"type": "text", "text": "ok"}]})

    await _summarizer(handler).summarize("texte")
    assert isinstance(seen["system"], str) and seen["system"]
    assert seen["messages"] == [{"role": "user", "content": "texte"}]


async def test_summarize_truncates_a_very_long_article() -> None:
    seen: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen.update(json.loads(request.content))
        return httpx.Response(200, json={"content": [{"type": "text", "text": "ok"}]})

    await _summarizer(handler).summarize("a" * 20_000)
    assert len(seen["messages"][0]["content"]) == 12_000  # type: ignore[index]


async def test_summarize_raises_on_an_error_status() -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, text="invalid x-api-key")

    with pytest.raises(LlmApiError):
        await _summarizer(handler).summarize("texte")


async def test_summarize_raises_when_only_non_text_blocks_come_back() -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"content": [{"type": "thinking", "thinking": "hmm"}]})

    with pytest.raises(LlmApiError):
        await _summarizer(handler).summarize("texte")


async def test_summarize_logs_the_url_and_the_status_of_a_rejected_call(
    caplog: pytest.LogCaptureFixture,
) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, text="invalid x-api-key")

    summarizer = AnthropicChatClient(
        api_key="wrong", model="claude-test", transport=httpx.MockTransport(handler)
    )
    with caplog.at_level(logging.WARNING), pytest.raises(LlmApiError):
        await summarizer.summarize("Un texte a resumer")

    record = caplog.records[-1]
    assert record.service == "anthropic"  # type: ignore[attr-defined]
    assert record.status_code == 401  # type: ignore[attr-defined]
    assert record.url.endswith("/messages")  # type: ignore[attr-defined]
