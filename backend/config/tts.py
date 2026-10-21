from functools import lru_cache

from pydantic_settings import BaseSettings


class TtsConfig(BaseSettings):
    """Ceilings on server-side speech, the one feature that stores audio and bills a reader's key."""

    # An article past this is read by the browser voice instead: a very long one would cost the
    # reader a lot on their own key, and the synthesised file would dwarf the text it came from.
    tts_max_chars: int = 30_000
    tts_max_audio_mb: int = 25
    # Oldest audio is dropped first once an account goes past this, so the cache never grows
    # without bound.
    tts_cache_mb_per_account: int = 100
    tts_rate_limit_max_attempts: int = 20
    tts_rate_limit_window_minutes: int = 60
    # A self-hosted speech server lives on a private address, which the outbound guard refuses by
    # default. An operator who runs one opts in here, for the whole instance.
    tts_allow_private_endpoints: bool = False


@lru_cache
def get_tts_config() -> TtsConfig:
    return TtsConfig()
