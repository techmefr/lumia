from collections.abc import AsyncIterator
from datetime import UTC, datetime

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from api.domain.article.models import Article, ArticleKeyword, Author, Category, Keyword, Lang
from api.domain.feed.models import Feed, SourceType
from api.domain.user.models import Instance, User
from config.database import get_engine
from worker.domain.pipeline.enrich_article import enrich_article
from worker.technical.connectors.base import RawArticle

FRENCH_CONTENT = (
    "<p>Le chat est dans le jardin avec la souris et il mangeait des croquettes. "
    "Le jardin est grand et le chat aime jouer avec la souris dans le jardin. "
    "Une troisieme phrase decrit encore le chat et le jardin en detail ici.</p>"
)


@pytest.fixture
async def session(db_schema: None) -> AsyncIterator[AsyncSession]:
    session_factory = async_sessionmaker(get_engine(), expire_on_commit=False)
    async with session_factory() as db_session:
        yield db_session


async def _create_feed(session: AsyncSession, *, external_feed_id: str = "10") -> Feed:
    instance = Instance(max_accounts=10, disk_quota_mb=1000)
    session.add(instance)
    await session.flush()
    user = User(
        instance_id=instance.id, email="user@example.com", username="user", password_hash=None
    )
    session.add(user)
    await session.flush()
    feed = Feed(
        user_id=user.id,
        source_type=SourceType.MINIFLUX,
        external_feed_id=external_feed_id,
        title="Feed",
        url="https://example.com/feed",
    )
    session.add(feed)
    await session.commit()
    return feed


def _raw_article(**overrides: object) -> RawArticle:
    defaults: dict[str, object] = {
        "source_type": "miniflux",
        "feed_external_id": "10",
        "external_entry_id": "123",
        "title": "Le chat et le jardin",
        "url": "https://example.com/a",
        "content": FRENCH_CONTENT,
        "published_at": datetime(2026, 8, 12, 10, 0, tzinfo=UTC),
        "author_name": "Jane Doe",
        "category_name": "Animaux",
    }
    defaults.update(overrides)
    return RawArticle(**defaults)  # type: ignore[arg-type]


async def test_enrich_article_creates_the_article_with_summary_and_keywords(
    session: AsyncSession,
) -> None:
    feed = await _create_feed(session)

    await enrich_article({}, _raw_article())

    article = await session.scalar(select(Article).where(Article.feed_id == feed.id))
    assert article is not None
    assert article.title == "Le chat et le jardin"
    assert article.summary
    assert len(article.summary) < len(article.content)

    keywords = await session.scalars(
        select(ArticleKeyword).where(ArticleKeyword.article_id == article.id)
    )
    assert len(list(keywords)) > 0


async def test_enrich_article_links_author_and_category(session: AsyncSession) -> None:
    await _create_feed(session)
    await enrich_article({}, _raw_article())

    author = await session.scalar(select(Author).where(Author.name == "Jane Doe"))
    category = await session.scalar(select(Category).where(Category.name == "Animaux"))
    assert author is not None
    assert category is not None

    article = await session.scalar(select(Article).where(Article.author_id == author.id))
    assert article is not None
    assert article.category_id == category.id


async def test_enrich_article_detects_french_and_stems_keywords_accordingly(
    session: AsyncSession,
) -> None:
    await _create_feed(session)
    await enrich_article({}, _raw_article())

    article = await session.scalar(select(Article))
    assert article is not None
    keyword_ids = [
        row.keyword_id
        for row in await session.scalars(
            select(ArticleKeyword).where(ArticleKeyword.article_id == article.id)
        )
    ]
    keywords = await session.scalars(select(Keyword).where(Keyword.id.in_(keyword_ids)))
    assert all(keyword.lang == Lang.FR for keyword in keywords)


async def test_enrich_article_reuses_an_existing_keyword_across_articles(
    session: AsyncSession,
) -> None:
    await _create_feed(session)
    await enrich_article({}, _raw_article(external_entry_id="1"))
    await enrich_article({}, _raw_article(external_entry_id="2"))

    chat_keywords = list(await session.scalars(select(Keyword).where(Keyword.term == "chat")))
    assert len(chat_keywords) == 1


async def test_enrich_article_is_idempotent_for_the_same_entry(session: AsyncSession) -> None:
    await _create_feed(session)
    await enrich_article({}, _raw_article())
    await enrich_article({}, _raw_article())

    articles = list(await session.scalars(select(Article)))
    assert len(articles) == 1


ENGLISH_CONTENT = (
    "<p>The cat is in the garden with the mouse and it was eating some biscuits. "
    "The garden is big and the cat likes to play with the mouse in the garden. "
    "A third sentence describes the cat and the garden in more detail here.</p>"
)


class _FakeTranslator:
    async def translate(self, text: str, *, target_lang: str) -> str:
        return f"[{target_lang}] {text}"


async def test_enrich_article_translates_foreign_content_to_the_users_preferred_language(
    session: AsyncSession,
) -> None:
    await _create_feed(session)

    await enrich_article(
        {},
        _raw_article(title="The cat", content=ENGLISH_CONTENT),
        translator=_FakeTranslator(),
    )

    article = await session.scalar(select(Article))
    assert article is not None
    assert article.title.startswith("[fr]")
    assert article.original_lang == Lang.EN


async def test_enrich_article_does_not_translate_when_language_already_matches(
    session: AsyncSession,
) -> None:
    await _create_feed(session)

    await enrich_article({}, _raw_article(), translator=_FakeTranslator())

    article = await session.scalar(select(Article))
    assert article is not None
    assert article.title == "Le chat et le jardin"
    assert article.original_lang == Lang.FR


async def test_enrich_article_extracts_english_keywords_from_the_original_text(
    session: AsyncSession,
) -> None:
    await _create_feed(session)

    await enrich_article(
        {},
        _raw_article(title="The cat", content=ENGLISH_CONTENT),
        translator=_FakeTranslator(),
    )

    article = await session.scalar(select(Article))
    assert article is not None
    keyword_ids = [
        row.keyword_id
        for row in await session.scalars(
            select(ArticleKeyword).where(ArticleKeyword.article_id == article.id)
        )
    ]
    keywords = await session.scalars(select(Keyword).where(Keyword.id.in_(keyword_ids)))
    assert all(keyword.lang == Lang.EN for keyword in keywords)


async def test_enrich_article_creates_one_article_per_subscribing_user(
    session: AsyncSession,
) -> None:
    await _create_feed(session, external_feed_id="20")

    instance = await session.scalar(select(Instance))
    assert instance is not None
    other_user = User(
        instance_id=instance.id,
        email="other@example.com",
        username="other",
        password_hash=None,
    )
    session.add(other_user)
    await session.flush()
    other_feed = Feed(
        user_id=other_user.id,
        source_type=SourceType.MINIFLUX,
        external_feed_id="20",
        title="Feed",
        url="https://example.com/feed",
    )
    session.add(other_feed)
    await session.commit()

    await enrich_article({}, _raw_article(feed_external_id="20"))

    articles = list(await session.scalars(select(Article)))
    assert len(articles) == 2


async def test_enrich_article_translates_per_subscriber_preferred_language(
    session: AsyncSession,
) -> None:
    fr_feed = await _create_feed(session, external_feed_id="30")

    instance = await session.scalar(select(Instance))
    assert instance is not None
    en_user = User(
        instance_id=instance.id,
        email="en-reader@example.com",
        username="en-reader",
        password_hash=None,
        preferred_language=Lang.EN,
    )
    session.add(en_user)
    await session.flush()
    en_feed = Feed(
        user_id=en_user.id,
        source_type=SourceType.MINIFLUX,
        external_feed_id="30",
        title="Feed",
        url="https://example.com/feed",
    )
    session.add(en_feed)
    await session.commit()

    await enrich_article(
        {},
        _raw_article(
            feed_external_id="30", title="The cat", content=ENGLISH_CONTENT
        ),
        translator=_FakeTranslator(),
    )

    fr_article = await session.scalar(select(Article).where(Article.feed_id == fr_feed.id))
    en_article = await session.scalar(select(Article).where(Article.feed_id == en_feed.id))
    assert fr_article is not None
    assert en_article is not None
    assert fr_article.title == "[fr] The cat"
    assert en_article.title == "The cat"
