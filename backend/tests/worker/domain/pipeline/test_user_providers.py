import httpx
import pytest

from api.domain.user.models import AIProvider, TranslationProvider, User
from api.technical.crypto.secret_box import encrypt_secret
from worker.domain.pipeline.enrich_article import _summarize, _summarizer_for, _translator_for
from worker.technical.ai.llm_client import LlmApiError

LONG_ENOUGH_TEXT = (
    "Le chat est dans le jardin. Le jardin est grand et calme. Une troisieme phrase suit."
)


def _user(**overrides: object) -> User:
    user = User(email="user@example.com", username="user")
    for field, value in overrides.items():
        setattr(user, field, value)
    return user


def test_translator_for_a_user_without_a_key_uses_the_instance_one() -> None:
    translator = _translator_for(_user(translation_api_key_encrypted=None))
    assert translator._api_key is None


def test_translator_for_a_user_with_a_key_uses_that_key() -> None:
    user = _user(
        translation_provider=TranslationProvider.DEEPL,
        translation_api_key_encrypted=encrypt_secret("deepl-secret"),
    )
    assert _translator_for(user)._api_key == "deepl-secret"


def test_translator_for_no_user_at_all_still_works() -> None:
    assert _translator_for(None)._api_key is None


def test_summarizer_for_a_user_without_a_provider_is_none() -> None:
    assert _summarizer_for(_user()) is None


def test_summarizer_for_a_provider_without_a_key_is_none() -> None:
    assert _summarizer_for(_user(ai_provider=AIProvider.MISTRAL)) is None


def test_summarizer_for_a_custom_provider_without_an_endpoint_is_none() -> None:
    user = _user(
        ai_provider=AIProvider.CUSTOM,
        ai_api_key_encrypted=encrypt_secret("sk-secret"),
        ai_model="voxtral-small",
    )
    assert _summarizer_for(user) is None


def test_summarizer_for_a_custom_provider_without_a_model_is_none() -> None:
    user = _user(
        ai_provider=AIProvider.CUSTOM,
        ai_api_key_encrypted=encrypt_secret("sk-secret"),
        ai_endpoint_url="http://voxtral.local/v1",
    )
    assert _summarizer_for(user) is None


def test_summarizer_for_a_fully_configured_user_is_built() -> None:
    user = _user(
        ai_provider=AIProvider.MISTRAL, ai_api_key_encrypted=encrypt_secret("sk-secret")
    )
    summarizer = _summarizer_for(user)
    assert summarizer is not None
    assert summarizer._api_key == "sk-secret"
    assert summarizer._base_url == "https://api.mistral.ai/v1"
    assert summarizer._model == "mistral-small-latest"


async def test_summarize_without_a_summarizer_falls_back_to_the_extractive_one() -> None:
    summary = await _summarize(LONG_ENOUGH_TEXT, None)
    assert summary
    assert "chat" in summary


async def test_summarize_uses_the_llm_when_one_is_configured() -> None:
    class _Fake:
        async def summarize(self, text: str) -> str:
            return "Résumé par le modèle."

    assert await _summarize(LONG_ENOUGH_TEXT, _Fake()) == "Résumé par le modèle."


@pytest.mark.parametrize(
    "error", [LlmApiError("rejected"), httpx.ConnectError("provider unreachable")]
)
async def test_summarize_falls_back_when_the_provider_fails(error: Exception) -> None:
    class _Failing:
        async def summarize(self, text: str) -> str:
            raise error

    summary = await _summarize(LONG_ENOUGH_TEXT, _Failing())
    assert "chat" in summary


async def test_summarize_falls_back_when_the_llm_returns_nothing() -> None:
    class _Empty:
        async def summarize(self, text: str) -> str:
            return "   "

    summary = await _summarize(LONG_ENOUGH_TEXT, _Empty())
    assert "chat" in summary
