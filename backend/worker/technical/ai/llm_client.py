import httpx

# Mistral, OpenAI and most self-hosted servers (vLLM, Ollama, LM Studio, Voxtral) all speak the
# same /chat/completions shape, so one client covers the three providers we offer.
_PROVIDER_BASE_URLS = {
    "mistral": "https://api.mistral.ai/v1",
    "openai": "https://api.openai.com/v1",
}
_DEFAULT_MODELS = {
    "mistral": "mistral-small-latest",
    "openai": "gpt-4o-mini",
}
_PROMPT = (
    "Résume cet article en trois phrases maximum, dans la langue de l'article. "
    "Ne commence pas par « Cet article » et n'ajoute aucun commentaire."
)
# Long articles blow the context window and the bill for no gain: the opening of a piece
# carries its subject.
_MAX_INPUT_CHARS = 12_000
_TIMEOUT_SECONDS = 60.0


class LlmApiError(Exception):
    pass


def resolve_base_url(provider: str, endpoint_url: str | None) -> str | None:
    """The base url for a provider, or None when the configuration can't produce one."""
    if provider == "custom":
        return endpoint_url.rstrip("/") if endpoint_url else None
    return _PROVIDER_BASE_URLS.get(provider)


def resolve_model(provider: str, model: str | None) -> str | None:
    """A self-hosted endpoint has no default we could guess, so it has to be named."""
    return model or _DEFAULT_MODELS.get(provider)


class OpenAiCompatibleSummarizer:
    def __init__(
        self,
        *,
        api_key: str,
        base_url: str,
        model: str,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._api_key = api_key
        self._base_url = base_url
        self._model = model
        self._transport = transport

    async def summarize(self, text: str) -> str:
        async with httpx.AsyncClient(
            base_url=self._base_url,
            headers={"Authorization": f"Bearer {self._api_key}"},
            transport=self._transport,
            timeout=_TIMEOUT_SECONDS,
        ) as client:
            response = await client.post(
                "/chat/completions",
                json={
                    "model": self._model,
                    "messages": [
                        {"role": "system", "content": _PROMPT},
                        {"role": "user", "content": text[:_MAX_INPUT_CHARS]},
                    ],
                },
            )
            if response.status_code >= 400:
                raise LlmApiError(response.text)
            choices = response.json().get("choices") or []
            if not choices:
                raise LlmApiError("no choice returned")
            return str(choices[0]["message"]["content"]).strip()
