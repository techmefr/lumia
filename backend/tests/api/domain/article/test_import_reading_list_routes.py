from collections.abc import AsyncIterator

import httpx
import pytest

from api.main import app
from tests.fake_arq_pool import FakeArqPool
from worker.technical.queue import get_arq_pool

ADMIN_PAYLOAD = {
    "email": "admin@example.com",
    "username": "admin",
    "password": "correct-horse-battery-staple",
}
POCKET = (
    b'<ul><li><a href="https://example.com/a">A</a></li>'
    b'<li><a href="https://example.com/b">B</a></li></ul>'
)


@pytest.fixture
def pool() -> FakeArqPool:
    return FakeArqPool()


@pytest.fixture
async def client(db_schema: None, pool: FakeArqPool) -> AsyncIterator[httpx.AsyncClient]:
    app.dependency_overrides[get_arq_pool] = lambda: pool
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as async_client:
        yield async_client
    app.dependency_overrides.clear()


async def _headers(client: httpx.AsyncClient) -> dict[str, str]:
    response = await client.post("/onboarding/admin", json=ADMIN_PAYLOAD)
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


async def _upload(
    client: httpx.AsyncClient, headers: dict[str, str], source: str, data: bytes
) -> httpx.Response:
    return await client.post(
        "/articles/import-reading-list",
        data={"source": source},
        files={"file": ("export", data, "application/octet-stream")},
        headers=headers,
    )


async def test_an_upload_is_accepted_and_handed_to_the_worker(
    client: httpx.AsyncClient, pool: FakeArqPool
) -> None:
    headers = await _headers(client)

    response = await _upload(client, headers, "pocket", POCKET)

    assert response.status_code == 202
    body = response.json()
    assert body["total"] == 2
    function, args, kwargs = pool.enqueued[0]
    assert function == "import_reading_list"
    assert args[1:] == (body["import_id"], ["https://example.com/a", "https://example.com/b"])
    assert kwargs["_job_timeout"] > 0


async def test_progress_reports_the_counts_the_worker_recorded(
    client: httpx.AsyncClient, pool: FakeArqPool
) -> None:
    headers = await _headers(client)
    import_id = (await _upload(client, headers, "pocket", POCKET)).json()["import_id"]

    first = await client.get(f"/articles/import-reading-list/{import_id}", headers=headers)
    await pool.hincrby(f"reading-import:{import_id}", "saved")
    await pool.hincrby(f"reading-import:{import_id}", "failed")
    second = await client.get(f"/articles/import-reading-list/{import_id}", headers=headers)

    assert first.json() == {"total": 2, "saved": 0, "failed": 0, "finished": False}
    assert second.json() == {"total": 2, "saved": 1, "failed": 1, "finished": True}


async def test_an_empty_export_queues_nothing(client: httpx.AsyncClient, pool: FakeArqPool) -> None:
    headers = await _headers(client)

    response = await _upload(client, headers, "wallabag", b"[]")

    assert response.json()["total"] == 0
    assert pool.enqueued == []


async def test_an_unknown_import_is_not_found(client: httpx.AsyncClient) -> None:
    headers = await _headers(client)

    response = await client.get("/articles/import-reading-list/nope", headers=headers)

    assert response.status_code == 404


async def test_a_malformed_export_is_refused(client: httpx.AsyncClient) -> None:
    headers = await _headers(client)

    response = await _upload(client, headers, "wallabag", b"not json")

    assert response.status_code == 400


async def test_an_unknown_source_is_refused(client: httpx.AsyncClient) -> None:
    headers = await _headers(client)

    response = await _upload(client, headers, "readwise", POCKET)

    assert response.status_code == 422


async def test_an_oversized_upload_is_refused(client: httpx.AsyncClient) -> None:
    headers = await _headers(client)

    response = await _upload(client, headers, "pocket", b"<!-- x -->" * 600_000)

    assert response.status_code == 413


async def test_too_many_links_are_refused(client: httpx.AsyncClient) -> None:
    headers = await _headers(client)
    links = "".join(f'<a href="https://example.com/{n}">x</a>' for n in range(2001))

    response = await _upload(client, headers, "pocket", links.encode())

    assert response.status_code == 413


async def test_the_import_requires_a_login(client: httpx.AsyncClient) -> None:
    response = await _upload(client, {}, "pocket", POCKET)

    assert response.status_code == 401
