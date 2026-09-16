from datetime import datetime, timedelta
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from api.domain.user.models import DigestFrequency, User
from config.digest import get_digest_config

FALLBACK_TIMEZONE = "UTC"

_LOOKBACK: dict[DigestFrequency, timedelta] = {
    DigestFrequency.DAILY: timedelta(days=1),
    DigestFrequency.WEEKLY: timedelta(days=7),
}


def reader_zone(name: str) -> ZoneInfo:
    """Falls back to UTC rather than raising: a bad tz name must not cost the reader their digest."""
    try:
        return ZoneInfo(name)
    except (ZoneInfoNotFoundError, ValueError):
        return ZoneInfo(FALLBACK_TIMEZONE)


def period_key(frequency: DigestFrequency, local_now: datetime) -> str:
    """Names the period the reader is currently in, in their own calendar.

    Daily is the local date, weekly the local ISO week. Both are derived from wall-clock time in
    the reader's zone, so a digest stays anchored to their day even across a DST change.
    """
    if frequency is DigestFrequency.WEEKLY:
        year, week, _ = local_now.isocalendar()
        return f"{year}-W{week:02d}"
    return local_now.date().isoformat()


def is_due(user: User, now: datetime) -> bool:
    """Whether this reader is owed a digest at `now`.

    Two conditions, and the order matters. The hour gate is what keeps the send at the time the
    reader chose; the period gate is what makes it idempotent, since re-entering a period that was
    already mailed is exactly what a worker restart or a manual re-run looks like.

    An hour missed because the worker was down is not silently written off either: the period
    stays unspent, so the next run that reaches the chosen hour inside it still sends. For a weekly
    reader that means the day after; for a daily one, the next morning.
    """
    if user.digest_frequency is DigestFrequency.NEVER:
        return False
    local_now = now.astimezone(reader_zone(user.digest_timezone))
    if local_now.hour != user.digest_hour:
        return False
    return user.digest_last_period != period_key(user.digest_frequency, local_now)


def window_start(user: User, now: datetime) -> datetime:
    """The oldest article a digest may report on.

    The last send, so nothing is reported twice and nothing published during an outage is lost;
    bounded by a maximum lookback, so a first digest is a digest and not a backlog.
    """
    floor = now - timedelta(days=get_digest_config().digest_max_lookback_days)
    if user.digest_last_sent_at is None:
        return max(floor, now - _LOOKBACK.get(user.digest_frequency, timedelta(days=1)))
    return max(floor, user.digest_last_sent_at)
