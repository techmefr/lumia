from collections.abc import AsyncIterator
from datetime import UTC, datetime

import httpx
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from api.domain.article import routes as article_routes
from api.domain.article.models import Article
from api.domain.feed.models import Feed, SourceType
from api.domain.recommendation.models import FilterMode, UserFilterRule
from api.domain.user.models import User
from api.main import app
from config.database import get_engine

ADMIN_PAYLOAD = {
    "email": "admin@example.com",
    "username": "admin",
    "password": "correct-horse-battery-staple",
}


@pytest.fixture
async def client(db_schema: None) -> AsyncIterator[httpx.AsyncClient]:
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as async_client:
        yield async_client


@pytest.fixture
def small_ranking_pool(monkeypatch: pytest.MonkeyPatch) -> None:
    """Shrinks the scoring window so a page past it needs a handful of rows, not five hundred."""
    monkeypatch.setattr(article_routes, "_RANKING_POOL", 5)


async def _headers(client: httpx.AsyncClient) -> dict[str, str]:
    response = await client.post("/onboarding/admin", json=ADMIN_PAYLOAD)
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


async def _seed(
    session: AsyncSession, *, count: int, muted_term: str | None = None, summaries: bool = True
) -> None:
    user = (await session.scalars(select(User))).one()
    feed = Feed(
        user_id=user.id,
        source_type=SourceType.MINIFLUX,
        external_feed_id="seeded",
        title="Seeded",
        url="https://example.com/feed",
    )
    session.add(feed)
    await session.flush()

    for index in range(count):
        session.add(
            Article(
                feed_id=feed.id,
                external_entry_id=f"entry-{index}",
                title=f"Article {index:03d}",
                url=f"https://example.com/entry-{index}",
                content="Content",
                summary=f"Summary {index:03d}" if summaries else None,
                published_at=datetime(2026, 8, 1, 12, index // 60, index % 60, tzinfo=UTC),
            )
        )
    if muted_term is not None:
        session.add(UserFilterRule(user_id=user.id, term=muted_term, mode=FilterMode.MUTE))
    await session.commit()


async def _seeded(**kwargs: object) -> None:
    session_factory = async_sessionmaker(get_engine(), expire_on_commit=False)
    async with session_factory() as session:
        await _seed(session, **kwargs)  # type: ignore[arg-type]


def _titles(response: httpx.Response) -> list[str]:
    return [article["title"] for article in response.json()]


async def test_a_mute_rule_no_longer_ends_the_feed_at_the_ranking_pool(
    client: httpx.AsyncClient, small_ranking_pool: None
) -> None:
    headers = await _headers(client)
    await _seeded(count=30, muted_term="article 007")

    page = await client.get("/articles", params={"limit": 5, "offset": 20}, headers=headers)

    assert page.status_code == 200
    assert len(_titles(page)) == 5


async def test_a_mute_rule_hides_the_matching_articles_and_keeps_the_page_full(
    client: httpx.AsyncClient,
) -> None:
    headers = await _headers(client)
    await _seeded(count=10, muted_term="article 009")

    page = await client.get("/articles", params={"limit": 5}, headers=headers)

    titles = _titles(page)
    assert "Article 009" not in titles
    assert len(titles) == 5


async def test_an_article_without_a_summary_survives_a_mute_rule(
    client: httpx.AsyncClient,
) -> None:
    headers = await _headers(client)
    await _seeded(count=3, muted_term="nothing-matches", summaries=False)

    page = await client.get("/articles", headers=headers)

    assert len(_titles(page)) == 3


async def test_a_mute_rule_matches_the_summary_too(client: httpx.AsyncClient) -> None:
    headers = await _headers(client)
    await _seeded(count=3, muted_term="summary 001")

    page = await client.get("/articles", headers=headers)

    assert _titles(page) == ["Article 002", "Article 000"]


async def test_relevance_pagination_reaches_past_the_ranking_pool(
    client: httpx.AsyncClient, small_ranking_pool: None
) -> None:
    headers = await _headers(client)
    await _seeded(count=12)

    page = await client.get(
        "/articles", params={"sort": "relevance", "limit": 4, "offset": 8}, headers=headers
    )

    assert page.status_code == 200
    assert len(_titles(page)) == 4
