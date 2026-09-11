"""Multi-turn exchanges, on both client shapes.

A discussion is the first caller that needs more than one turn, and the first that needs to know
what it spent.
"""

import httpx
import pytest

from worker.technical.ai.anthropic_client import AnthropicChatClient
from worker.technical.ai.base import LlmApiError, Turn
from worker.technical.ai.llm_client import OpenAiCompatibleChatClient

TURNS = [
    Turn(role="user", content="Explique le second paragraphe."),
    Turn(role="assistant", content="Il parle du financement."),
    Turn(role="user", content="Par qui ?"),
]


def _openai_client(handler: httpx.MockTransport) -> OpenAiCompatibleChatClient:
    return OpenAiCompatibleChatClient(
        api_key="secret", base_url="https://api.test/v1", model="a-model", transport=handler
    )


async def test_an_openai_compatible_exchange_carries_the_system_prompt_and_every_turn() -> None:
    sent: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        import json

        sent.update(json.loads(request.content))
        return httpx.Response(
            200,
            json={
                "choices": [{"message": {"content": " La région. "}}],
                "usage": {"total_tokens": 1234},
            },
        )

    answer = await _openai_client(httpx.MockTransport(handler)).converse(
        system="Voici l'article.", turns=TURNS
    )

    assert answer.text == "La région."
    assert answer.tokens_used == 1234
    assert sent["messages"] == [
        {"role": "system", "content": "Voici l'article."},
        {"role": "user", "content": "Explique le second paragraphe."},
        {"role": "assistant", "content": "Il parle du financement."},
        {"role": "user", "content": "Par qui ?"},
    ]


async def test_an_openai_compatible_exchange_without_a_usage_block_reports_no_count() -> None:
    """Saying nothing beats inventing a figure the reader would take for their bill."""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"choices": [{"message": {"content": "La région."}}]})

    answer = await _openai_client(httpx.MockTransport(handler)).converse(
        system="Voici l'article.", turns=TURNS
    )

    assert answer.tokens_used is None


async def test_an_openai_compatible_refusal_raises() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, text="invalid api key")

    with pytest.raises(LlmApiError):
        await _openai_client(httpx.MockTransport(handler)).converse(system="s", turns=TURNS)


async def test_an_anthropic_exchange_keeps_the_system_prompt_out_of_the_turns() -> None:
    """Anthropic takes the system prompt as a field of its own, not as a message."""
    sent: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        import json

        sent.update(json.loads(request.content))
        return httpx.Response(
            200,
            json={
                "content": [{"type": "text", "text": "La région."}],
                "usage": {"input_tokens": 900, "output_tokens": 34},
            },
        )

    client = AnthropicChatClient(
        api_key="secret", model="a-model", transport=httpx.MockTransport(handler)
    )
    answer = await client.converse(system="Voici l'article.", turns=TURNS)

    assert answer.text == "La région."
    assert answer.tokens_used == 934
    assert sent["system"] == "Voici l'article."
    assert sent["messages"] == [
        {"role": "user", "content": "Explique le second paragraphe."},
        {"role": "assistant", "content": "Il parle du financement."},
        {"role": "user", "content": "Par qui ?"},
    ]


async def test_an_anthropic_refusal_raises() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(429, text="rate limited")

    client = AnthropicChatClient(
        api_key="secret", model="a-model", transport=httpx.MockTransport(handler)
    )
    with pytest.raises(LlmApiError):
        await client.converse(system="s", turns=TURNS)
