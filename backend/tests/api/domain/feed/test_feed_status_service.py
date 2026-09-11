from datetime import UTC, datetime
from uuid import uuid4

from api.domain.feed.feed_status_service import apply_feed_status, classify_error_reason
from api.domain.feed.models import Feed, SourceType


def _feed() -> Feed:
    return Feed(
        user_id=uuid4(),
        source_type=SourceType.MINIFLUX,
        external_feed_id="1",
        title="A blog",
        url="https://blog.test/rss",
        error_count=0,
    )


class TestClassifyErrorReason:
    def test_a_certificate_problem_is_classified(self) -> None:
        assert classify_error_reason("x509: certificate has expired or is not yet valid") == (
            "certificate"
        )

    def test_a_timeout_is_classified_as_unreachable(self) -> None:
        assert classify_error_reason("Client.Timeout exceeded while awaiting headers") == (
            "unreachable"
        )

    def test_a_404_is_classified_as_not_found(self) -> None:
        assert classify_error_reason("Unable to download feed (404 Not Found)") == "not_found"

    def test_a_403_is_classified_as_forbidden(self) -> None:
        assert classify_error_reason("403 Forbidden") == "forbidden"

    def test_a_malformed_feed_is_classified_as_unparsable(self) -> None:
        assert classify_error_reason("Unable to parse XML: invalid character") == "unparsable"

    def test_anything_else_falls_back_to_unknown(self) -> None:
        assert classify_error_reason("something Miniflux never documented") == "unknown"


class TestApplyFeedStatus:
    def test_a_feed_going_from_ok_to_broken_gets_a_since_timestamp(self) -> None:
        feed = _feed()
        now = datetime(2026, 9, 11, 8, 0, tzinfo=UTC)

        apply_feed_status(feed, error_count=3, error_message="404 Not Found", now=now)

        assert feed.error_count == 3
        assert feed.error_reason == "not_found"
        assert feed.error_since == now

    def test_a_feed_still_broken_keeps_its_original_since_timestamp(self) -> None:
        feed = _feed()
        first_seen = datetime(2026, 9, 1, 8, 0, tzinfo=UTC)
        apply_feed_status(feed, error_count=1, error_message="404 Not Found", now=first_seen)

        later = datetime(2026, 9, 11, 8, 0, tzinfo=UTC)
        apply_feed_status(feed, error_count=7, error_message="404 Not Found", now=later)

        assert feed.error_count == 7
        assert feed.error_since == first_seen

    def test_a_recovered_feed_is_cleared_entirely(self) -> None:
        feed = _feed()
        broke_at = datetime(2026, 9, 1, 8, 0, tzinfo=UTC)
        apply_feed_status(feed, error_count=1, error_message="404 Not Found", now=broke_at)

        apply_feed_status(
            feed, error_count=0, error_message="", now=datetime(2026, 9, 11, tzinfo=UTC)
        )

        assert feed.error_count == 0
        assert feed.error_reason is None
        assert feed.error_since is None

    def test_a_feed_that_was_never_broken_stays_untouched(self) -> None:
        feed = _feed()

        apply_feed_status(feed, error_count=0, error_message="", now=datetime.now(UTC))

        assert feed.error_count == 0
        assert feed.error_reason is None
        assert feed.error_since is None
