from functools import lru_cache

from pydantic_settings import BaseSettings


class MaintenanceConfig(BaseSettings):
    """The scheduled housekeeping the worker runs on its own."""

    # A day covers any outage short enough to go unnoticed, without asking Miniflux for its whole
    # history on every pass.
    reconciliation_window_hours: int = 24
    reconciliation_max_entries: int = 500
    # Long enough that an expired token is still recognised as expired rather than as unknown.
    token_purge_grace_days: int = 7


@lru_cache
def get_maintenance_config() -> MaintenanceConfig:
    return MaintenanceConfig()
