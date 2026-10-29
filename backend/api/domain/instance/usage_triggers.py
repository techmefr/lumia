from sqlalchemy import Connection, event, text
from sqlalchemy.sql.expression import FromClause

FUNCTION_NAME = "lumia_article_usage_apply"
TRIGGER_NAME = "trg_articles_stored_bytes"

CREATE_FUNCTION = f"""
CREATE OR REPLACE FUNCTION {FUNCTION_NAME}() RETURNS trigger AS $body$
BEGIN
    IF TG_OP IN ('DELETE', 'UPDATE') THEN
        UPDATE users SET stored_bytes = stored_bytes - (
            octet_length(OLD.content) + octet_length(coalesce(OLD.summary, ''))
        )
        WHERE id = (SELECT user_id FROM feeds WHERE id = OLD.feed_id);
    END IF;
    IF TG_OP IN ('INSERT', 'UPDATE') THEN
        UPDATE users SET stored_bytes = stored_bytes + (
            octet_length(NEW.content) + octet_length(coalesce(NEW.summary, ''))
        )
        WHERE id = (SELECT user_id FROM feeds WHERE id = NEW.feed_id);
        RETURN NEW;
    END IF;
    RETURN OLD;
END;
$body$ LANGUAGE plpgsql
"""

CREATE_TRIGGER = f"""
CREATE TRIGGER {TRIGGER_NAME}
AFTER INSERT OR DELETE OR UPDATE OF content, summary, feed_id ON articles
FOR EACH ROW EXECUTE FUNCTION {FUNCTION_NAME}()
"""

BACKFILL = """
UPDATE users SET stored_bytes = COALESCE((
    SELECT SUM(octet_length(articles.content) + octet_length(COALESCE(articles.summary, '')))
    FROM articles JOIN feeds ON feeds.id = articles.feed_id
    WHERE feeds.user_id = users.id
), 0)
"""

DROP_TRIGGER = f"DROP TRIGGER IF EXISTS {TRIGGER_NAME} ON articles"
DROP_FUNCTION = f"DROP FUNCTION IF EXISTS {FUNCTION_NAME}()"


def keep_stored_bytes_in_step(articles: FromClause) -> None:
    @event.listens_for(articles, "after_create")
    def create_usage_trigger(target: FromClause, connection: Connection, **kwargs: object) -> None:
        connection.execute(text(CREATE_FUNCTION))
        connection.execute(text(CREATE_TRIGGER))
