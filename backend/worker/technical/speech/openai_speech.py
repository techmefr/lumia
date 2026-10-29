import logging

import httpx

from api.technical.logging.external import log_external_failure
from api.technical.net.pinned_transport import guarded_transport
from api.technical.net.url_guard import Resolver, resolve_with_system
from worker.technical.speech.base import SpeechApiError, SynthesizedAudio

SERVICE_NAME = "openai-speech"
TIMEOUT_SECONDS = 120.0
# The speech endpoint refuses an input past 4096 characters, so a long article goes in pieces.
MAX_INPUT_CHARS = 4000
MAX_AUDIO_BYTES = 25 * 1024 * 1024

OPENAI_BASE_URL = "https://api.openai.com/v1"
DEFAULT_MODEL = "tts-1"
DEFAULT_VOICE = "alloy"

logger = logging.getLogger(__name__)


def split_for_speech(text: str, limit: int = MAX_INPUT_CHARS) -> list[str]:
    """Pieces no longer than `limit`, cut after a sentence end when there is one to cut at."""
    pieces: list[str] = []
    rest = text.strip()
    while len(rest) > limit:
        window = rest[:limit]
        cut = max(window.rfind(". "), window.rfind("! "), window.rfind("? "))
        if cut < limit // 2:
            cut = window.rfind(" ")
        end = cut + 1 if cut > 0 else limit
        pieces.append(rest[:end].strip())
        rest = rest[end:].strip()
    if rest:
        pieces.append(rest)
    return pieces


class OpenAiSpeechSynthesizer:
    """Any server speaking OpenAI's /audio/speech: OpenAI itself, or a self-hosted one."""

    def __init__(
        self,
        *,
        api_key: str,
        base_url: str,
        model: str,
        voice: str,
        max_audio_bytes: int = MAX_AUDIO_BYTES,
        transport: httpx.AsyncBaseTransport | None = None,
        pin_to_public_addresses: bool = False,
        resolve: Resolver = resolve_with_system,
    ) -> None:
        self._api_key = api_key
        self._base_url = base_url
        self._model = model
        self._voice = voice
        self._max_audio_bytes = max_audio_bytes
        self._transport = transport
        self._pin = pin_to_public_addresses
        self._resolve = resolve

    @property
    def base_url(self) -> str:
        return self._base_url

    @property
    def cache_key(self) -> str:
        return f"{self._base_url}|{self._model}|{self._voice}"

    async def synthesize(self, text: str) -> SynthesizedAudio:
        parts: list[bytes] = []
        size = 0
        async with httpx.AsyncClient(
            base_url=self._base_url,
            headers={"Authorization": f"Bearer {self._api_key}"},
            transport=guarded_transport(self._transport, self._resolve)
            if self._pin
            else self._transport,
            timeout=TIMEOUT_SECONDS,
        ) as client:
            for piece in split_for_speech(text):
                response = await client.post(
                    "/audio/speech",
                    json={
                        "model": self._model,
                        "voice": self._voice,
                        "input": piece,
                        "response_format": "mp3",
                    },
                )
                if response.status_code >= 400:
                    log_external_failure(
                        logger,
                        service=SERVICE_NAME,
                        operation="synthesize",
                        url=str(response.request.url),
                        status_code=response.status_code,
                    )
                    raise SpeechApiError(f"speech provider answered {response.status_code}")
                size += len(response.content)
                if size > self._max_audio_bytes:
                    raise SpeechApiError("synthesised audio exceeds the size ceiling")
                parts.append(response.content)
        if not parts:
            raise SpeechApiError("nothing to synthesise")
        # MP3 frames are self-contained, so the pieces play back to back as one file.
        return SynthesizedAudio(content_type="audio/mpeg", data=b"".join(parts))
