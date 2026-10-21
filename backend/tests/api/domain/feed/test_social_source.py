import pytest

from api.domain.feed.social_source import REDDIT_USER_AGENT, resolve_social_feed


@pytest.mark.parametrize(
    ("address", "expected"),
    [
        ("https://mastodon.social/@Gargron", "https://mastodon.social/@Gargron.rss"),
        ("https://mastodon.social/@Gargron/", "https://mastodon.social/@Gargron.rss"),
        ("@Gargron@mastodon.social", "https://mastodon.social/@Gargron.rss"),
        ("https://fosstodon.org/tags/python", "https://fosstodon.org/tags/python.rss"),
        ("#python@fosstodon.org", "https://fosstodon.org/tags/python.rss"),
        (
            "https://bsky.app/profile/alice.bsky.social",
            "https://bsky.app/profile/alice.bsky.social/rss",
        ),
        ("@alice.bsky.social", "https://bsky.app/profile/alice.bsky.social/rss"),
        ("https://www.reddit.com/r/python/top/?t=week", "https://www.reddit.com/r/python/.rss"),
        ("https://old.reddit.com/r/python", "https://www.reddit.com/r/python/.rss"),
        ("r/python", "https://www.reddit.com/r/python/.rss"),
        ("/r/python/", "https://www.reddit.com/r/python/.rss"),
        ("https://www.reddit.com/user/spez/submitted", "https://www.reddit.com/user/spez/.rss"),
        ("u/spez", "https://www.reddit.com/user/spez/.rss"),
        (
            "https://news.google.com/search?q=climate%20change&hl=en",
            "https://news.google.com/rss/search?q=climate%20change",
        ),
        ("news:climate change", "https://news.google.com/rss/search?q=climate%20change"),
    ],
)
def test_a_supported_address_resolves_to_its_public_rss(address: str, expected: str) -> None:
    resolved = resolve_social_feed(address)

    assert resolved is not None
    assert resolved.url == expected


def test_only_reddit_carries_a_dedicated_user_agent() -> None:
    reddit = resolve_social_feed("r/python")
    mastodon = resolve_social_feed("@Gargron@mastodon.social")

    assert reddit is not None
    assert reddit.user_agent == REDDIT_USER_AGENT
    assert mastodon is not None
    assert mastodon.user_agent is None


@pytest.mark.parametrize(
    "address",
    [
        "https://hnrss.org/frontpage",
        "https://example.com/blog/post",
        "https://www.youtube.com/@MrBeast",
        "https://medium.com/@someone",
        "https://www.reddit.com/",
        "https://news.google.com/topstories",
        "https://bsky.app/",
        "",
        "not a feed",
    ],
)
def test_anything_else_is_left_to_the_regular_feed_flow(address: str) -> None:
    assert resolve_social_feed(address) is None
