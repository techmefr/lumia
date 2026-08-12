import httpx

from config.deepl import get_deepl_config


class DeeplApiError(Exception):
    pass


def get_deepl_transport() -> httpx.AsyncBaseTransport | None:
    return None


class DeeplTranslator:
    def __init__(self, *, transport: httpx.AsyncBaseTransport | None = None) -> None:
        self._transport = transport

    async def translate(self, text: str, *, target_lang: str) -> str:
        config = get_deepl_config()
        async with httpx.AsyncClient(
            base_url=config.deepl_base_url,
            headers={"Authorization": f"DeepL-Auth-Key {config.deepl_api_key}"},
            transport=self._transport,
        ) as client:
            response = await client.post(
                "/v2/translate",
                json={"text": [text], "target_lang": target_lang.upper()},
            )
            if response.status_code >= 400:
                raise DeeplApiError(response.text)
            return str(response.json()["translations"][0]["text"])
