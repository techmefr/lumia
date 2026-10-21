import re
import unicodedata
from urllib.parse import quote

_MAX_STEM_LENGTH = 80


def file_stem(title: str) -> str:
    """A title cut to a length every file system accepts, otherwise left as it was written."""
    return title.strip()[:_MAX_STEM_LENGTH] or "article"


def attachment_header(title: str, extension: str) -> str:
    """Builds a Content-Disposition that survives any title, accents and quotes included.

    The plain filename is ASCII for the clients that read only that one; the starred form carries
    the real title for those that understand RFC 5987.
    """
    stem = file_stem(title)
    folded = unicodedata.normalize("NFKD", stem).encode("ascii", "ignore").decode()
    ascii_stem = re.sub(r"[^A-Za-z0-9._-]+", "-", folded).strip("-") or "article"
    return (
        f'attachment; filename="{ascii_stem}.{extension}"; '
        f"filename*=UTF-8''{quote(stem)}.{extension}"
    )
