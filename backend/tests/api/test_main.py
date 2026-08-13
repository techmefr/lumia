import httpx
from fastapi import FastAPI

from api.main import app


def test_app_is_a_fastapi_instance() -> None:
    assert isinstance(app, FastAPI)


async def test_cors_preflight_allows_the_configured_web_origin() -> None:
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.options(
            "/onboarding/admin",
            headers={
                "origin": "http://localhost:5174",
                "access-control-request-method": "POST",
            },
        )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:5174"
