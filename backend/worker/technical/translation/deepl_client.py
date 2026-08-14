import httpx

from config.deepl import get_deepl_config
from worker.technical.translation.base import TranslationApiError


class DeeplApiError(TranslationApiError):
    pass


def get_deepl_transport() -> httpx.AsyncBaseTransport | None:
    return None


# DeepL names its targets its own way: regional variants for Portuguese, none for Chinese. Malagasy
# is absent from its catalogue entirely, so it has no entry rather than a wrong one — a reader who
# picks it keeps the original text instead of getting an API error per article.
TARGET_CODES = {
    "fr": "FR",
    "en": "EN-US",
    "es": "ES",
    "de": "DE",
    "it": "IT",
    "pt": "PT-PT",
    "ru": "RU",
    "ar": "AR",
    "zh": "ZH",
}


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

    def supports(self, target_lang: str) -> bool:
        return target_lang.lower() in TARGET_CODES

    async def translate(self, text: str, *, target_lang: str) -> str:
        code = TARGET_CODES.get(target_lang.lower())
        if code is None:
            raise DeeplApiError(f"deepl does not translate into {target_lang}")
        config = get_deepl_config()
        async with httpx.AsyncClient(
            base_url=config.deepl_base_url,
            headers={"Authorization": f"DeepL-Auth-Key {self._api_key or config.deepl_api_key}"},
            transport=self._transport,
        ) as client:
            response = await client.post(
                "/v2/translate",
                json={"text": [text], "target_lang": code},
            )
            if response.status_code >= 400:
                raise DeeplApiError(response.text)
            return str(response.json()["translations"][0]["text"])
