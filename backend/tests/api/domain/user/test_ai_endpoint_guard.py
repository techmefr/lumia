from collections.abc import AsyncIterator

import httpx
import pytest

from api.domain.user.models import AIProvider, User
from api.domain.user.providers import chat_client_for
from api.main import app
from api.technical.crypto.secret_box import encrypt_secret
from api.technical.net.url_guard import get_url_resolver
from config.chat import ChatConfig
from tests.api.domain.user.test_me_routes import _onboarded_headers
from worker.technical.ai.base import LlmApiError
from worker.technical.ai.llm_client import OpenAiCompatibleChatClient


@pytest.fixture
async def client(db_schema: None) -> AsyncIterator[httpx.AsyncClient]:
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as async_client:
        yield async_client


async def test_a_private_ai_endpoint_is_refused_when_saved(client: httpx.AsyncClient) -> None:
    headers = await _onboarded_headers(client)
    app.dependency_overrides[get_url_resolver] = lambda: lambda _host: ["10.0.0.5"]

    response = await client.patch(
        "/me",
        headers=headers,
        json={"ai_provider": "custom", "ai_endpoint_url": "http://ollama.lan/v1"},
    )

    assert response.status_code == 422
    assert response.json()["detail"] == "ai_endpoint_blocked"


async def test_a_private_ai_endpoint_is_saved_when_the_operator_allows_it(
    client: httpx.AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    headers = await _onboarded_headers(client)
    app.dependency_overrides[get_url_resolver] = lambda: lambda _host: ["10.0.0.5"]
    monkeypatch.setattr(
        "api.domain.user.routes.get_chat_config",
        lambda: ChatConfig(ai_allow_private_endpoints=True),
    )

    response = await client.patch(
        "/me",
        headers=headers,
        json={"ai_provider": "custom", "ai_endpoint_url": "http://ollama.lan/v1"},
    )

    assert response.status_code == 200


async def test_the_chat_client_never_connects_to_a_private_address() -> None:
    client = OpenAiCompatibleChatClient(
        api_key="k",
        base_url="http://rebind.example/v1",
        model="m",
        resolve=lambda _host: ["127.0.0.1"],
    )

    with pytest.raises(LlmApiError):
        await client.complete(system="s", user="u")


def test_the_operator_opt_in_reaches_the_chat_client(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "api.domain.user.providers.get_chat_config",
        lambda: ChatConfig(ai_allow_private_endpoints=True),
    )
    user = User(
        ai_provider=AIProvider.CUSTOM,
        ai_api_key_encrypted=encrypt_secret("k"),
        ai_endpoint_url="http://ollama.lan/v1",
        ai_model="m",
    )

    built = chat_client_for(user)

    assert isinstance(built, OpenAiCompatibleChatClient)
    assert built._allow_private_endpoints is True
