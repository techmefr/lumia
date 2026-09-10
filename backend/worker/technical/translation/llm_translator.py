"""Translation through the account's own LLM, for installs that have no DeepL key.

The model is asked for the target language by name rather than by code: a two-letter code is
ambiguous prose to a chat model, whereas a language name is not.
"""

import httpx

from worker.technical.ai.base import ChatClient, LlmApiError
from worker.technical.translation.base import TranslationApiError

#: One entry per reading language the app offers, Malagasy included: an LLM has no fixed catalogue
#: the way DeepL does, so this is the app's own list rather than a provider's.
LANGUAGE_NAMES = {
    "fr": "français",
    "en": "anglais",
    "es": "espagnol",
    "de": "allemand",
    "it": "italien",
    "pt": "portugais",
    "ru": "russe",
    "ar": "arabe",
    "zh": "chinois simplifié",
    "mg": "malgache",
}

#: A chat model answers a request; without this it comments on the text or wraps it in a preamble,
#: and the reader gets an apology instead of an article.
PROMPT_TEMPLATE = (
    "Traduis en {language} le texte que l'utilisateur envoie. "
    "Réponds uniquement par la traduction, sans préambule, sans commentaire et sans guillemets. "
    "Conserve la mise en forme, les sauts de ligne et les balises HTML telles quelles."
)

#: Past this the request stops being affordable and the answer stops fitting in the output budget.
#: Refused rather than truncated: half a translated article reads like a broken one.
MAX_TRANSLATABLE_CHARS = 12_000


class LlmTranslationError(TranslationApiError):
    pass


class LlmTranslator:
    def __init__(self, *, chat_client: ChatClient) -> None:
        self._chat_client = chat_client

    def supports(self, target_lang: str) -> bool:
        return target_lang.lower() in LANGUAGE_NAMES

    async def translate(self, text: str, *, target_lang: str) -> str:
        language = LANGUAGE_NAMES.get(target_lang.lower())
        if language is None:
            raise LlmTranslationError(f"no language name for {target_lang}")
        if len(text) > MAX_TRANSLATABLE_CHARS:
            raise LlmTranslationError(
                f"text of {len(text)} characters exceeds the {MAX_TRANSLATABLE_CHARS} limit"
            )
        try:
            translated = await self._chat_client.complete(
                system=PROMPT_TEMPLATE.format(language=language), user=text
            )
        except (LlmApiError, httpx.HTTPError) as exc:
            # Re-raised as a translation failure so a caller degrades without knowing which
            # provider it happened to be handed.
            raise LlmTranslationError(str(exc)) from exc
        if not translated.strip():
            raise LlmTranslationError("the model returned nothing")
        return translated.strip()
