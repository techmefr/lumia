from typing import Protocol


class TranslationApiError(Exception):
    """Raised by any provider client, so a caller can degrade without naming one."""


class Translator(Protocol):
    def supports(self, target_lang: str) -> bool:
        """Whether this provider can translate into `target_lang`.

        Asked before translating rather than discovered through an error: no provider covers every
        language a reader may pick, and the caller has to be able to keep the original instead.
        """
        ...

    async def translate(self, text: str, *, target_lang: str) -> str: ...
