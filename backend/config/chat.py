from functools import lru_cache

from pydantic_settings import BaseSettings


class ChatConfig(BaseSettings):
    """Ceilings on the article chat, which spends the reader's own key on every message."""

    chat_max_message_chars: int = 2_000
    # What the model is shown of the article: the opening carries the subject, and the rest is
    # the reader's bill.
    chat_max_article_chars: int = 12_000
    # Turns replayed to the model; older ones stay readable in the thread but are not paid for.
    chat_history_turns: int = 10
    # Stored per reader and article, the oldest dropped first so a thread never grows unbounded.
    chat_max_stored_messages: int = 100
    chat_rate_limit_max_attempts: int = 30
    chat_rate_limit_window_minutes: int = 60


@lru_cache
def get_chat_config() -> ChatConfig:
    return ChatConfig()
