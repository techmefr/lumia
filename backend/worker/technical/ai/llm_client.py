import logging

import httpx

from api.technical.logging.external import log_external_failure
from api.technical.net.pinned_transport import guarded_transport
from api.technical.net.url_guard import BlockedUrlError, Resolver, resolve_with_system
from worker.technical.ai.base import (
    MAX_INPUT_CHARS,
    SUMMARY_PROMPT,
    TIMEOUT_SECONDS,
    LlmApiError,
)

# Mistral, OpenAI and most self-hosted servers (vLLM, Ollama, LM Studio, Voxtral) all speak the
# same /chat/completions shape, so one client covers those providers. Anthropic does not, and has
# its own client next door.
_PROVIDER_BASE_URLS = {
    "mistral": "https://api.mistral.ai/v1",
    "openai": "https://api.openai.com/v1",
    # Googles own OpenAI-compatible endpoint, the same one that serves Gemini also serves the
    # hosted Gemma models under it.
    "gemma": "https://generativelanguage.googleapis.com/v1beta/openai",
}
_DEFAULT_MODELS = {
    "mistral": "mistral-small-latest",
    "openai": "gpt-4o-mini",
    "gemma": "gemma-3-27b-it",
}

SERVICE_NAME = "openai-compatible"

logger = logging.getLogger(__name__)

__all__ = ["LlmApiError", "OpenAiCompatibleChatClient", "resolve_base_url", "resolve_model"]


def resolve_base_url(provider: str, endpoint_url: str | None) -> str | None:
    """The base url for a provider, or None when the configuration can't produce one."""
    if provider == "custom":
        return endpoint_url.rstrip("/") if endpoint_url else None
    return _PROVIDER_BASE_URLS.get(provider)


def resolve_model(provider: str, model: str | None) -> str | None:
    """A self-hosted endpoint has no default we could guess, so it has to be named."""
    return model or _DEFAULT_MODELS.get(provider)


class OpenAiCompatibleChatClient:
    def __init__(
        self,
        *,
        api_key: str,
        base_url: str,
        model: str,
        transport: httpx.AsyncBaseTransport | None = None,
        allow_private_endpoints: bool = False,
        resolve: Resolver = resolve_with_system,
    ) -> None:
        self._api_key = api_key
        self._base_url = base_url
        self._model = model
        self._transport = transport
        self._allow_private_endpoints = allow_private_endpoints
        self._resolve = resolve

    def _guarded(self) -> httpx.AsyncBaseTransport | None:
        if self._allow_private_endpoints:
            return self._transport
        return guarded_transport(self._transport, self._resolve)

    async def complete(self, *, system: str, user: str) -> str:
        async with httpx.AsyncClient(
            base_url=self._base_url,
            headers={"Authorization": f"Bearer {self._api_key}"},
            transport=self._guarded(),
            timeout=TIMEOUT_SECONDS,
        ) as client:
            try:
                response = await client.post(
                    "/chat/completions",
                    json={
                        "model": self._model,
                        "messages": [
                            {"role": "system", "content": system},
                            {"role": "user", "content": user},
                        ],
                    },
                )
            except BlockedUrlError as exc:
                raise LlmApiError(f"endpoint blocked: {exc}") from exc
            if response.status_code >= 400:
                log_external_failure(
                    logger,
                    service=SERVICE_NAME,
                    operation="complete",
                    url=str(response.request.url),
                    status_code=response.status_code,
                )
                raise LlmApiError(response.text)
            choices = response.json().get("choices") or []
            if not choices:
                raise LlmApiError("no choice returned")
            return str(choices[0]["message"]["content"]).strip()

    async def summarize(self, text: str) -> str:
        return await self.complete(system=SUMMARY_PROMPT, user=text[:MAX_INPUT_CHARS])
