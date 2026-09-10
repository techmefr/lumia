from functools import lru_cache

from pydantic_settings import BaseSettings


class InstanceConfig(BaseSettings):
    """What the environment says about the instance at its very first start.

    The three admin fields are optional on purpose: absent, the browser onboarding screen stays
    the default path. The two quotas are only a starting point — once the instance row exists the
    admin owns those numbers, and a restart never writes them back.
    """

    admin_email: str | None = None
    admin_username: str | None = None
    admin_password: str | None = None
    max_accounts: int = 10
    account_quota_mb: int = 1000


@lru_cache
def get_instance_config() -> InstanceConfig:
    return InstanceConfig()
