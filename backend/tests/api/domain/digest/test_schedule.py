from datetime import UTC, datetime, timedelta
from uuid import uuid4

from api.domain.digest.schedule import is_due, period_key, reader_zone, window_start
from api.domain.user.models import DigestFrequency, User


def _reader(**overrides: object) -> User:
    defaults: dict[str, object] = {
        "instance_id": uuid4(),
        "email": "reader@example.com",
        "username": "reader",
        "digest_frequency": DigestFrequency.DAILY,
        "digest_hour": 8,
        "digest_timezone": "UTC",
        "digest_last_period": None,
        "digest_last_sent_at": None,
    }
    return User(**{**defaults, **overrides})


def test_a_reader_who_never_asked_is_never_due() -> None:
    reader = _reader(digest_frequency=DigestFrequency.NEVER, digest_hour=8)

    assert is_due(reader, datetime(2026, 9, 16, 8, 5, tzinfo=UTC)) is False


def test_the_chosen_hour_is_read_in_the_reader_own_timezone() -> None:
    reader = _reader(digest_timezone="Asia/Tokyo", digest_hour=8)

    # 23:05 UTC is 08:05 the next morning in Tokyo, which is the hour this reader asked for.
    assert is_due(reader, datetime(2026, 9, 15, 23, 5, tzinfo=UTC)) is True
    assert is_due(reader, datetime(2026, 9, 16, 8, 5, tzinfo=UTC)) is False


def test_a_second_run_in_the_same_period_is_not_due_again() -> None:
    now = datetime(2026, 9, 16, 8, 5, tzinfo=UTC)
    reader = _reader(digest_last_period="2026-09-16")

    assert is_due(reader, now) is False
    assert is_due(_reader(digest_last_period="2026-09-15"), now) is True


def test_a_weekly_reader_is_due_once_per_iso_week() -> None:
    reader = _reader(digest_frequency=DigestFrequency.WEEKLY)
    monday = datetime(2026, 9, 14, 8, 5, tzinfo=UTC)

    assert is_due(reader, monday) is True
    reader.digest_last_period = period_key(DigestFrequency.WEEKLY, monday)
    assert is_due(reader, monday) is False
    # Still the same ISO week two days later, so still nothing owed.
    assert is_due(reader, monday + timedelta(days=2)) is False
    assert is_due(reader, monday + timedelta(days=7)) is True


def test_the_period_key_names_a_day_or_a_week() -> None:
    moment = datetime(2026, 9, 16, 8, 0, tzinfo=UTC)

    assert period_key(DigestFrequency.DAILY, moment) == "2026-09-16"
    assert period_key(DigestFrequency.WEEKLY, moment) == "2026-W38"


def test_an_unresolvable_timezone_falls_back_to_utc() -> None:
    assert reader_zone("Mars/Olympus").key == "UTC"


def test_the_window_starts_at_the_last_send_and_never_before_the_lookback_floor() -> None:
    now = datetime(2026, 9, 16, 8, 5, tzinfo=UTC)
    last_send = now - timedelta(days=2)

    assert window_start(_reader(digest_last_sent_at=last_send), now) == last_send
    ancient = _reader(digest_last_sent_at=now - timedelta(days=365))
    assert window_start(ancient, now) > now - timedelta(days=30)


def test_a_first_daily_digest_reaches_back_one_day() -> None:
    now = datetime(2026, 9, 16, 8, 5, tzinfo=UTC)

    assert window_start(_reader(), now) == now - timedelta(days=1)
    weekly = _reader(digest_frequency=DigestFrequency.WEEKLY)
    assert window_start(weekly, now) == now - timedelta(days=7)
