import uuid
from contextvars import ContextVar, Token

CORRELATION_ID_FIELD = "correlation_id"
MAX_CORRELATION_ID_LENGTH = 64
_EXTRA_ALLOWED_CHARACTERS = frozenset("-_.")

_correlation_id: ContextVar[str | None] = ContextVar(CORRELATION_ID_FIELD, default=None)


def new_correlation_id() -> str:
    return uuid.uuid4().hex


def get_correlation_id() -> str | None:
    return _correlation_id.get()


def set_correlation_id(correlation_id: str) -> Token[str | None]:
    return _correlation_id.set(correlation_id)


def reset_correlation_id(token: Token[str | None]) -> None:
    _correlation_id.reset(token)


def sanitize_correlation_id(raw_correlation_id: str | None) -> str:
    """Accepts a caller-supplied id only when it is harmless, otherwise mints a fresh one.

    The id is echoed back in a response header and into every log line of the request, so a value
    carrying a newline or a control character could forge a header or a whole log entry.
    """
    if raw_correlation_id is None:
        return new_correlation_id()
    candidate = raw_correlation_id.strip()
    if not candidate or len(candidate) > MAX_CORRELATION_ID_LENGTH:
        return new_correlation_id()
    if not all(
        (character.isascii() and character.isalnum()) or character in _EXTRA_ALLOWED_CHARACTERS
        for character in candidate
    ):
        return new_correlation_id()
    return candidate
