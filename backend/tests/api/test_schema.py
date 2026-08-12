from sqlalchemy import inspect
from sqlalchemy.engine import Connection

from config.database import get_engine

EXPECTED_TABLES = {
    "instances",
    "users",
    "sessions",
    "folders",
    "feeds",
    "authors",
    "categories",
    "articles",
    "keywords",
    "article_keywords",
    "user_article_feedback",
    "user_keyword_scores",
    "user_feed_scores",
    "user_author_scores",
    "user_category_scores",
}


async def test_schema_creates_every_phase1_table(db_schema: None) -> None:
    engine = get_engine()
    async with engine.connect() as connection:
        table_names = await connection.run_sync(_get_table_names)
    assert EXPECTED_TABLES.issubset(set(table_names))


def _get_table_names(connection: Connection) -> list[str]:
    return inspect(connection).get_table_names()
