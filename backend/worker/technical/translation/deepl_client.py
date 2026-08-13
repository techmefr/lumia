import httpx

from config.deepl import get_deepl_config


class DeeplApiError(Exception):
    pass


def get_deepl_transport() -> httpx.AsyncBaseTransport | None:
    return None


class DeeplTranslator:
    def __init__(
        self,
        *,
        api_key: str | None = None,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        # A per-account key wins over the instance one: the account that reads is the account
        # that pays. The instance key stays as the fallback for a single-user install.
        self._api_key = api_key
        self._transport = transport

    async def translate(self, text: str, *, target_lang: str) -> str:
        config = get_deepl_config()
        async with httpx.AsyncClient(
            base_url=config.deepl_base_url,
            headers={"Authorization": f"DeepL-Auth-Key {self._api_key or config.deepl_api_key}"},
            transport=self._transport,
        ) as client:
            response = await client.post(
                "/v2/translate",
                json={"text": [text], "target_lang": target_lang.upper()},
            )
            if response.status_code >= 400:
                raise DeeplApiError(response.text)
            return str(response.json()["translations"][0]["text"])
