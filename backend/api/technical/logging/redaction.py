import logging
import re
from urllib.parse import parse_qsl, urlencode

REDACTED = "redacted"

_TOKEN_PATH = re.compile(r"^(/public/articles/|/inbound/newsletters/)[^/?#]+")
_SECRET_QUERY_PARAMETERS = frozenset(
    {"token", "magic_token", "api_key", "key", "secret", "code", "state", "password"}
)
_ACCESS_LOG_TARGET_INDEX = 2


def redact_path(path: str) -> str:
    return _TOKEN_PATH.sub(lambda match: f"{match.group(1)}{REDACTED}", path)


def redact_target(target: str) -> str:
    path, separator, query = target.partition("?")
    redacted_path = redact_path(path)
    if not separator:
        return redacted_path
    pairs = [
        (name, REDACTED if name.lower() in _SECRET_QUERY_PARAMETERS else value)
        for name, value in parse_qsl(query, keep_blank_values=True)
    ]
    return f"{redacted_path}?{urlencode(pairs)}"


class AccessLogRedactionFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.args, tuple) and len(record.args) > _ACCESS_LOG_TARGET_INDEX:
            arguments = list(record.args)
            target = arguments[_ACCESS_LOG_TARGET_INDEX]
            if isinstance(target, str):
                arguments[_ACCESS_LOG_TARGET_INDEX] = redact_target(target)
                record.args = tuple(arguments)
        return True
