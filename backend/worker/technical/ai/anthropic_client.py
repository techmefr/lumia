"""Anthropic's Messages API, which is not OpenAI-compatible.

Three differences make a separate client cheaper than bending the shared one: the key travels in
`x-api-key` rather than a bearer header, the version is a required header, and the system prompt is
a top-level field instead of a message with `role: system`.
"""

import logging

import httpx

from api.technical.logging.external import log_external_failure
from worker.technical.ai.base import (
    MAX_INPUT_CHARS,
    SUMMARY_PROMPT,
    TIMEOUT_SECONDS,
    LlmApiError,
)

BASE_URL = "https://api.anthropic.com/v1"
DEFAULT_MODEL = "claude-haiku-4-5-20251001"
#: Pinned rather than tracking latest: a silent shape change in the response would break the
#: pipeline for every self-hoster at once.
API_VERSION = "2023-06-01"
#: Sized for the longest answer this client is asked for, a whole translated article. A summary
#: stays short because its prompt says so, not because the ceiling cuts it off.
_MAX_OUTPUT_TOKENS = 8192
SERVICE_NAME = "anthropic"

logger = logging.getLogger(__name__)


class AnthropicChatClient:
    def __init__(
        self,
        *,
        api_key: str,
        model: str,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._api_key = api_key
        self._model = model
        self._transport = transport

    async def complete(self, *, system: str, user: str) -> str:
        async with httpx.AsyncClient(
            base_url=BASE_URL,
            headers={"x-api-key": self._api_key, "anthropic-version": API_VERSION},
            transport=self._transport,
            timeout=TIMEOUT_SECONDS,
        ) as client:
            response = await client.post(
                "/messages",
                json={
                    "model": self._model,
                    "max_tokens": _MAX_OUTPUT_TOKENS,
                    "system": system,
                    "messages": [{"role": "user", "content": user}],
                },
            )
            if response.status_code >= 400:
                log_external_failure(
                    logger,
                    service=SERVICE_NAME,
                    operation="complete",
                    url=str(response.request.url),
                    status_code=response.status_code,
                )
                raise LlmApiError(response.text)
            blocks = response.json().get("content") or []
            texts = [block.get("text", "") for block in blocks if block.get("type") == "text"]
            if not texts:
                raise LlmApiError("no text block returned")
            return "".join(texts).strip()

    async def summarize(self, text: str) -> str:
        return await self.complete(system=SUMMARY_PROMPT, user=text[:MAX_INPUT_CHARS])
