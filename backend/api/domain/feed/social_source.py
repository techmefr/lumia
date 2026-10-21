import re
from dataclasses import dataclass
from urllib.parse import parse_qs, quote, urlsplit

REDDIT_USER_AGENT = (
    "Lumia/1.0 (self-hosted feed reader; personal, non-commercial use of public RSS)"
)

_REDDIT_HOSTS = frozenset({"reddit.com", "www.reddit.com", "old.reddit.com", "np.reddit.com"})
_BLUESKY_HOSTS = frozenset({"bsky.app", "www.bsky.app"})
_NOT_MASTODON_HOSTS = frozenset(
    {
        "youtube.com",
        "www.youtube.com",
        "m.youtube.com",
        "medium.com",
        "tiktok.com",
        "www.tiktok.com",
        "threads.net",
        "www.threads.net",
        "bsky.app",
        "www.bsky.app",
    }
)
_GOOGLE_NEWS_HOST = "news.google.com"

_REDDIT_SUBREDDIT_PATH = re.compile(r"^/r/(\w{2,21})(?:/|$)")
_REDDIT_USER_PATH = re.compile(r"^/(?:user|u)/([\w-]{3,20})(?:/|$)")
_BLUESKY_PROFILE_PATH = re.compile(r"^/profile/([\w.\-]+)/?$")
_MASTODON_PROFILE_PATH = re.compile(r"^/@([\w.\-]+)/?$")
_MASTODON_TAG_PATH = re.compile(r"^/tags/([^/.]+)/?$")

_SHORT_REDDIT_SUBREDDIT = re.compile(r"^/?r/(\w{2,21})/?$")
_SHORT_REDDIT_USER = re.compile(r"^/?u(?:ser)?/([\w-]{3,20})/?$")
_SHORT_MASTODON_PROFILE = re.compile(r"^@([\w.\-]+)@([\w\-]+(?:\.[\w\-]+)+)$")
_SHORT_MASTODON_TAG = re.compile(r"^#([^\s@#]+)@([\w\-]+(?:\.[\w\-]+)+)$")
_SHORT_BLUESKY = re.compile(r"^@([\w\-]+(?:\.[\w\-]+)+)$")
_SHORT_GOOGLE_NEWS = re.compile(r"^news:\s*(.+)$", re.IGNORECASE)


@dataclass(frozen=True)
class SocialFeed:
    url: str
    user_agent: str | None = None


def _reddit(path: str) -> SocialFeed | None:
    subreddit = _REDDIT_SUBREDDIT_PATH.match(path) or _SHORT_REDDIT_SUBREDDIT.match(path)
    if subreddit is not None:
        return SocialFeed(f"https://www.reddit.com/r/{subreddit.group(1)}/.rss", REDDIT_USER_AGENT)
    user = _REDDIT_USER_PATH.match(path) or _SHORT_REDDIT_USER.match(path)
    if user is not None:
        return SocialFeed(f"https://www.reddit.com/user/{user.group(1)}/.rss", REDDIT_USER_AGENT)
    return None


def _google_news(query: str) -> SocialFeed:
    return SocialFeed(f"https://news.google.com/rss/search?q={quote(query.strip())}")


def _from_short_form(text: str) -> SocialFeed | None:
    if (reddit := _reddit(text)) is not None:
        return reddit
    if (match := _SHORT_MASTODON_PROFILE.match(text)) is not None:
        return SocialFeed(f"https://{match.group(2)}/@{match.group(1)}.rss")
    if (match := _SHORT_MASTODON_TAG.match(text)) is not None:
        return SocialFeed(f"https://{match.group(2)}/tags/{match.group(1)}.rss")
    if (match := _SHORT_BLUESKY.match(text)) is not None:
        return SocialFeed(f"https://bsky.app/profile/{match.group(1)}/rss")
    if (match := _SHORT_GOOGLE_NEWS.match(text)) is not None:
        return _google_news(match.group(1))
    return None


def resolve_social_feed(address: str) -> SocialFeed | None:
    """Turns a profile, subreddit, hashtag or search address into the public RSS feed behind it.

    Returns None when the address is not one of the supported social sources, so the caller keeps
    treating it as a plain feed or site address. No request is made: each source publishes its feed
    at a fixed path, so the mapping is pure.
    """
    text = address.strip()
    if not text:
        return None
    if "://" not in text:
        return _from_short_form(text)
    parts = urlsplit(text)
    host = (parts.hostname or "").lower()
    path = parts.path
    if host in _REDDIT_HOSTS:
        return _reddit(path)
    if host == _GOOGLE_NEWS_HOST:
        query = parse_qs(parts.query).get("q")
        if path.rstrip("/") == "/search" and query:
            return _google_news(query[0])
        return None
    if host in _BLUESKY_HOSTS:
        profile = _BLUESKY_PROFILE_PATH.match(path)
        if profile is not None:
            return SocialFeed(f"https://bsky.app/profile/{profile.group(1)}/rss")
        return None
    if host in _NOT_MASTODON_HOSTS or not host:
        return None
    if (profile := _MASTODON_PROFILE_PATH.match(path)) is not None:
        return SocialFeed(f"https://{parts.netloc}/@{profile.group(1)}.rss")
    if (tag := _MASTODON_TAG_PATH.match(path)) is not None:
        return SocialFeed(f"https://{parts.netloc}/tags/{tag.group(1)}.rss")
    return None
