from api.technical.logging.correlation import (
    MAX_CORRELATION_ID_LENGTH,
    get_correlation_id,
    reset_correlation_id,
    sanitize_correlation_id,
    set_correlation_id,
)


def test_set_then_reset_restores_the_previous_value() -> None:
    assert get_correlation_id() is None
    token = set_correlation_id("abc123")
    assert get_correlation_id() == "abc123"
    reset_correlation_id(token)
    assert get_correlation_id() is None


def test_keeps_a_plausible_client_supplied_id() -> None:
    assert sanitize_correlation_id("req-42_b.1") == "req-42_b.1"


def test_mints_an_id_when_the_client_sent_none() -> None:
    assert sanitize_correlation_id(None)


def test_mints_an_id_rather_than_trusting_a_forged_one() -> None:
    forged = "abc\r\nX-Admin: true"
    assert sanitize_correlation_id(forged) != forged


def test_mints_an_id_rather_than_echoing_an_oversized_one() -> None:
    oversized = "a" * (MAX_CORRELATION_ID_LENGTH + 1)
    assert sanitize_correlation_id(oversized) != oversized


def test_mints_an_id_rather_than_echoing_a_blank_one() -> None:
    assert sanitize_correlation_id("   ")


def test_mints_an_id_rather_than_echoing_a_non_ascii_one() -> None:
    """The id goes back out as a header value, where a non latin-1 character breaks the response."""
    assert sanitize_correlation_id("idé") != "idé"
