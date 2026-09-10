import httpx
import pytest

from worker.domain.pipeline.enrich_article import _summarize
from worker.technical.ai.llm_client import LlmApiError

LONG_ENOUGH_TEXT = (
    "Le chat est dans le jardin. Le jardin est grand et calme. Une troisieme phrase suit."
)


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
