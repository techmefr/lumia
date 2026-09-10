from collections.abc import Iterator

import pytest

from api.domain.user.models import AIProvider, TranslationProvider, User
from api.domain.user.providers import chat_client_for, translator_for
from api.technical.crypto.secret_box import encrypt_secret
from config.deepl import get_deepl_config
from worker.technical.ai.anthropic_client import DEFAULT_MODEL as ANTHROPIC_DEFAULT_MODEL
from worker.technical.ai.anthropic_client import AnthropicChatClient
from worker.technical.ai.llm_client import OpenAiCompatibleChatClient
from worker.technical.translation.deepl_client import DeeplTranslator
from worker.technical.translation.llm_translator import LlmTranslator


def _user(**overrides: object) -> User:
    user = User(email="user@example.com", username="user")
    for field, value in overrides.items():
        setattr(user, field, value)
    return user


@pytest.fixture
def without_an_instance_deepl_key(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    monkeypatch.delenv("DEEPL_API_KEY", raising=False)
    get_deepl_config.cache_clear()
    yield
    get_deepl_config.cache_clear()


def test_translator_for_a_user_without_a_key_uses_the_instance_one() -> None:
    translator = translator_for(_user(translation_api_key_encrypted=None))
    assert isinstance(translator, DeeplTranslator)
    assert translator._api_key is None


def test_translator_for_a_user_with_a_deepl_key_uses_that_key() -> None:
    user = _user(
        translation_provider=TranslationProvider.DEEPL,
        translation_api_key_encrypted=encrypt_secret("deepl-secret"),
    )
    translator = translator_for(user)
    assert isinstance(translator, DeeplTranslator)
    assert translator._api_key == "deepl-secret"


def test_translator_for_no_user_at_all_still_works() -> None:
    translator = translator_for(None)
    assert isinstance(translator, DeeplTranslator)
    assert translator._api_key is None


def test_an_explicit_deepl_choice_wins_over_the_configured_ai() -> None:
    user = _user(
        translation_provider=TranslationProvider.DEEPL,
        translation_api_key_encrypted=encrypt_secret("deepl-secret"),
        ai_provider=AIProvider.MISTRAL,
        ai_api_key_encrypted=encrypt_secret("sk-secret"),
    )
    assert isinstance(translator_for(user), DeeplTranslator)


def test_a_configured_ai_translates_and_wins_over_the_instance_deepl_key() -> None:
    """The issue this closes: an account with an LLM key but no DeepL key could not translate."""
    user = _user(ai_provider=AIProvider.MISTRAL, ai_api_key_encrypted=encrypt_secret("sk-secret"))
    assert isinstance(translator_for(user), LlmTranslator)


@pytest.mark.usefixtures("without_an_instance_deepl_key")
def test_translator_for_an_install_with_no_key_at_all_is_none() -> None:
    """A clean outcome, not an exception: articles stay in their original language."""
    assert translator_for(_user()) is None


@pytest.mark.usefixtures("without_an_instance_deepl_key")
def test_translator_for_an_incomplete_ai_configuration_is_none() -> None:
    user = _user(ai_provider=AIProvider.CUSTOM, ai_api_key_encrypted=encrypt_secret("sk-secret"))
    assert translator_for(user) is None


@pytest.mark.usefixtures("without_an_instance_deepl_key")
def test_a_user_deepl_key_still_works_without_an_instance_key() -> None:
    user = _user(
        translation_provider=TranslationProvider.DEEPL,
        translation_api_key_encrypted=encrypt_secret("deepl-secret"),
    )
    assert isinstance(translator_for(user), DeeplTranslator)


def test_chat_client_for_a_user_without_a_provider_is_none() -> None:
    assert chat_client_for(_user()) is None


def test_chat_client_for_a_provider_without_a_key_is_none() -> None:
    assert chat_client_for(_user(ai_provider=AIProvider.MISTRAL)) is None


def test_chat_client_for_a_custom_provider_without_an_endpoint_is_none() -> None:
    user = _user(
        ai_provider=AIProvider.CUSTOM,
        ai_api_key_encrypted=encrypt_secret("sk-secret"),
        ai_model="voxtral-small",
    )
    assert chat_client_for(user) is None


def test_chat_client_for_a_custom_provider_without_a_model_is_none() -> None:
    user = _user(
        ai_provider=AIProvider.CUSTOM,
        ai_api_key_encrypted=encrypt_secret("sk-secret"),
        ai_endpoint_url="http://voxtral.local/v1",
    )
    assert chat_client_for(user) is None


def test_chat_client_for_a_fully_configured_user_is_built() -> None:
    user = _user(ai_provider=AIProvider.MISTRAL, ai_api_key_encrypted=encrypt_secret("sk-secret"))
    client = chat_client_for(user)
    # Narrowed rather than asserted loosely: only the OpenAI-compatible client carries a base url,
    # and picking the wrong client for a provider is exactly what this test is here to catch.
    assert isinstance(client, OpenAiCompatibleChatClient)
    assert client._api_key == "sk-secret"
    assert client._base_url == "https://api.mistral.ai/v1"
    assert client._model == "mistral-small-latest"


def test_chat_client_for_a_gemma_user_uses_googles_openai_compatible_endpoint() -> None:
    user = _user(ai_provider=AIProvider.GEMMA, ai_api_key_encrypted=encrypt_secret("gm-secret"))
    client = chat_client_for(user)
    assert isinstance(client, OpenAiCompatibleChatClient)
    assert client._api_key == "gm-secret"
    assert client._base_url == "https://generativelanguage.googleapis.com/v1beta/openai"
    assert client._model == "gemma-3-27b-it"


def test_chat_client_for_an_anthropic_user_uses_the_messages_client() -> None:
    user = _user(
        ai_provider=AIProvider.ANTHROPIC, ai_api_key_encrypted=encrypt_secret("sk-ant-secret")
    )
    client = chat_client_for(user)
    assert isinstance(client, AnthropicChatClient)
    assert client._api_key == "sk-ant-secret"
    assert client._model == ANTHROPIC_DEFAULT_MODEL
