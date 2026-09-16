import pytest

from api.technical.net.canonical_url import canonical_url


@pytest.mark.parametrize(
    ("url", "expected"),
    [
        ("https://example.com/article", "https://example.com/article"),
        ("http://example.com/article", "https://example.com/article"),
        ("https://www.example.com/article", "https://example.com/article"),
        ("https://EXAMPLE.com/Article", "https://example.com/Article"),
        ("https://example.com/article/", "https://example.com/article"),
        ("https://example.com/", "https://example.com"),
        ("https://example.com:443/article", "https://example.com/article"),
        ("http://example.com:80/article", "https://example.com/article"),
        ("https://example.com:8443/article", "https://example.com:8443/article"),
        ("https://example.com/article#section", "https://example.com/article"),
        ("  https://example.com/article  ", "https://example.com/article"),
    ],
)
def test_it_normalises_the_parts_that_never_change_the_article(url: str, expected: str) -> None:
    assert canonical_url(url) == expected


@pytest.mark.parametrize(
    "url",
    [
        "https://example.com/article?utm_source=newsletter&utm_campaign=august",
        "https://example.com/article?fbclid=abc123",
        "https://example.com/article?gclid=abc&msclkid=def",
        "https://example.com/article?ref=aggregator",
        "https://example.com/article?xtor=RSS-1",
        "https://example.com/article?pk_campaign=rss",
        "https://example.com/article?_hsenc=xyz&_hsmi=42",
    ],
)
def test_it_drops_the_parameters_that_only_say_where_the_click_came_from(url: str) -> None:
    assert canonical_url(url) == "https://example.com/article"


@pytest.mark.parametrize(
    "url",
    [
        "https://example.com/?p=123",
        "https://example.com/?id=42",
        "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        "https://example.com/index.php?story_fbid=7&page=2",
    ],
)
def test_it_keeps_the_parameters_that_identify_the_content(url: str) -> None:
    canonical = canonical_url(url)
    for parameter in url.split("?")[1].split("&"):
        assert parameter in canonical


def test_it_keeps_a_content_parameter_while_dropping_the_tracking_one_next_to_it() -> None:
    assert (
        canonical_url("https://example.com/?p=123&utm_source=twitter")
        == "https://example.com?p=123"
    )


def test_it_ignores_the_order_the_parameters_arrived_in() -> None:
    assert canonical_url("https://example.com/a?b=2&a=1") == canonical_url(
        "https://example.com/a?a=1&b=2"
    )


def test_it_leaves_alone_what_it_cannot_read_as_a_web_address() -> None:
    assert canonical_url("mailto:reader@example.com") == "mailto:reader@example.com"
    assert canonical_url("not a url") == "not a url"
    assert canonical_url("https://example.com:port/a") == "https://example.com:port/a"
