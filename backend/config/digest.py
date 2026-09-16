from functools import lru_cache

from pydantic_settings import BaseSettings


class DigestConfig(BaseSettings):
    """The shape of the periodic digest the worker mails to readers who asked for one."""

    # A digest is a nudge, not an archive: past a dozen entries nobody reads to the end, and the
    # ranking has already put the best ones first.
    digest_max_articles: int = 10
    # How far back a first digest, or one that follows a long silence, is allowed to reach. Without
    # it an account that opts in after a year of reading would get a mail spanning that year.
    digest_max_lookback_days: int = 14


@lru_cache
def get_digest_config() -> DigestConfig:
    return DigestConfig()
