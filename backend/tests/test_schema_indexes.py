import pytest
from sqlalchemy import text

from config.database import get_engine

EXPECTED_INDEXES = {
    ("articles", "feed_id"),
    ("articles", "published_at"),
    ("articles", "author_id"),
    ("articles", "category_id"),
    ("feeds", "user_id"),
    ("feeds", "external_feed_id"),
    ("feeds", "folder_id"),
    ("folders", "user_id"),
    ("article_keywords", "keyword_id"),
    ("user_article_feedback", "article_id"),
    ("refresh_tokens", "user_id"),
    ("refresh_tokens", "expires_at"),
    ("magic_link_tokens", "user_id"),
}


@pytest.mark.parametrize(("table", "column"), sorted(EXPECTED_INDEXES))
async def test_the_hot_query_columns_are_indexed(db_schema: None, table: str, column: str) -> None:
    async with get_engine().connect() as connection:
        found = await connection.scalar(
            text("SELECT count(*) FROM pg_indexes WHERE tablename = :table AND indexname = :name"),
            {"table": table, "name": f"ix_{table}_{column}"},
        )

    assert found == 1


async def test_emails_are_unique_whatever_their_case(db_schema: None) -> None:
    async with get_engine().connect() as connection:
        found = await connection.scalar(
            text("SELECT count(*) FROM pg_indexes WHERE indexname = :name"),
            {"name": "uq_users_email_lower"},
        )

    assert found == 1
