from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

_HTTP_SCHEMES = frozenset({"http", "https"})
_CANONICAL_SCHEME = "https"
_DEFAULT_PORTS = {"http": 80, "https": 443}

# Prefixes and names that only say where a click came from. Anything outside this list is kept:
# a query parameter is part of the article's identity far more often than it is noise
# (`?p=123`, `?id=42`, `?v=` on YouTube, `?story_fbid=`…), and dropping one merges two articles
# that were never the same.
_TRACKING_PREFIXES = ("utm_", "pk_", "mtm_", "piwik_", "_hs", "at_", "ga_")
_TRACKING_PARAMS = frozenset(
    {
        "cmpid",
        "dclid",
        "ef_id",
        "fbclid",
        "gbraid",
        "gclid",
        "igshid",
        "ito",
        "mc_cid",
        "mc_eid",
        "msclkid",
        "ncid",
        "oly_anon_id",
        "oly_enc_id",
        "ref",
        "ref_src",
        "ref_url",
        "s_kwcid",
        "sr_share",
        "twclid",
        "vero_conv",
        "vero_id",
        "wbraid",
        "wt_mc",
        "wt_zmc",
        "xtor",
        "yclid",
    }
)


def canonical_url(url: str) -> str:
    """Reduces a URL to the identity of the article behind it.

    Two feeds republishing the same piece hand out the same address dressed differently — one over
    http and the other over https, one with `www.`, one with a trailing slash, most of them with a
    campaign tag appended. Everything that survives here is something a site can serve a different
    article from, so the result is safe to compare for equality.
    """
    stripped = url.strip()
    parts = urlsplit(stripped)
    try:
        port = parts.port
    except ValueError:
        # A port that is not a number: nothing here can make sense of the address, and the raw
        # string still compares equal to itself.
        return stripped
    if parts.scheme.lower() not in _HTTP_SCHEMES or not parts.hostname:
        return stripped

    host = parts.hostname.removeprefix("www.")
    port = _explicit_port(parts.scheme.lower(), port)
    netloc = f"{host}:{port}" if port is not None else host
    path = parts.path.rstrip("/")
    query = urlencode(sorted(_content_params(parts.query)))
    return urlunsplit((_CANONICAL_SCHEME, netloc, path, query, ""))


def _explicit_port(scheme: str, port: int | None) -> int | None:
    if port is None or port == _DEFAULT_PORTS[scheme]:
        return None
    return port


def _content_params(query: str) -> list[tuple[str, str]]:
    return [
        (name, value)
        for name, value in parse_qsl(query, keep_blank_values=True)
        if not _is_tracking(name)
    ]


def _is_tracking(name: str) -> bool:
    lowered = name.lower()
    return lowered in _TRACKING_PARAMS or lowered.startswith(_TRACKING_PREFIXES)
