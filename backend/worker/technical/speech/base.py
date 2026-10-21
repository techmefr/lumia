from dataclasses import dataclass
from typing import Protocol


class SpeechApiError(Exception):
    """Raised by any speech provider, so a caller can fall back without naming one."""


@dataclass(frozen=True)
class SynthesizedAudio:
    content_type: str
    data: bytes


class SpeechSynthesizer(Protocol):
    @property
    def cache_key(self) -> str:
        """Identifies what the audio sounds like, so a changed voice never serves an old file."""
        ...

    @property
    def base_url(self) -> str:
        """Where the audio is requested from, which the caller checks before any request leaves."""
        ...

    async def synthesize(self, text: str) -> SynthesizedAudio: ...
