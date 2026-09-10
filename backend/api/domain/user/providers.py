"""Which provider an account actually gets, from what it has actually configured.

Shared by the ingestion pipeline and the on-demand translation endpoint so the two never disagree
about what a reader is entitled to.
"""

from fastapi import Depends

from api.domain.user.dependencies import get_current_user
from api.domain.user.models import AIProvider, TranslationProvider, User
from api.technical.crypto.secret_box import decrypt_secret
from config.deepl import get_deepl_config
from worker.technical.ai.anthropic_client import DEFAULT_MODEL as ANTHROPIC_DEFAULT_MODEL
from worker.technical.ai.anthropic_client import AnthropicChatClient
from worker.technical.ai.base import ChatClient
from worker.technical.ai.llm_client import (
    OpenAiCompatibleChatClient,
    resolve_base_url,
    resolve_model,
)
from worker.technical.translation.base import Translator
from worker.technical.translation.deepl_client import DeeplTranslator
from worker.technical.translation.llm_translator import LlmTranslator


def chat_client_for(user: User | None) -> ChatClient | None:
    """The account's own LLM, or None to fall back on whatever local behaviour the caller has.

    A provider without a key, or a self-hosted endpoint with no url or model, is an incomplete
    configuration: it falls back rather than failing the caller.
    """
    if user is None or user.ai_provider is None or user.ai_api_key_encrypted is None:
        return None
    if user.ai_provider is AIProvider.ANTHROPIC:
        return AnthropicChatClient(
            api_key=decrypt_secret(user.ai_api_key_encrypted),
            model=user.ai_model or ANTHROPIC_DEFAULT_MODEL,
        )
    base_url = resolve_base_url(user.ai_provider.value, user.ai_endpoint_url)
    model = resolve_model(user.ai_provider.value, user.ai_model)
    if base_url is None or model is None:
        return None
    return OpenAiCompatibleChatClient(
        api_key=decrypt_secret(user.ai_api_key_encrypted), base_url=base_url, model=model
    )


def translator_for(user: User | None) -> Translator | None:
    """The translator this account gets, or None when nothing is configured to translate with.

    Their own DeepL key comes first because choosing DeepL is an explicit choice, their LLM next
    because it is a key they already pay for, and the instance-wide DeepL key last. None is a
    supported outcome, not an error: an install with no key at all keeps articles in their original
    language instead of failing on every one of them.
    """
    if (
        user is not None
        and user.translation_provider is TranslationProvider.DEEPL
        and user.translation_api_key_encrypted is not None
    ):
        return DeeplTranslator(api_key=decrypt_secret(user.translation_api_key_encrypted))
    chat_client = chat_client_for(user)
    if chat_client is not None:
        return LlmTranslator(chat_client=chat_client)
    if get_deepl_config().deepl_api_key is None:
        return None
    return DeeplTranslator()


def get_translator(user: User = Depends(get_current_user)) -> Translator | None:
    return translator_for(user)
