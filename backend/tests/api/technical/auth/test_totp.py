from datetime import UTC, datetime, timedelta
from unittest.mock import patch

import pyotp

from api.technical.auth.totp import (
    DRIFT_STEPS,
    RECOVERY_CODE_COUNT,
    build_enrolment,
    generate_recovery_codes,
    generate_totp_secret,
    normalise_recovery_code,
    verify_totp_code,
)

SECRET = "JBSWY3DPEHPK3PXP"
STEP_SECONDS = 30


def _code_at(moment: datetime, secret: str = SECRET) -> str:
    return pyotp.TOTP(secret).at(moment)


def _step_at(moment: datetime, secret: str = SECRET) -> int:
    return pyotp.TOTP(secret).timecode(moment)


def test_a_freshly_drawn_secret_is_usable_base32() -> None:
    secret = generate_totp_secret()

    assert verify_totp_code(secret, _code_at(datetime.now(UTC), secret)) is not None


def test_the_enrolment_uri_names_the_account_and_the_issuer() -> None:
    enrolment = build_enrolment(SECRET, account_name="reader@example.com", issuer="Lumia")

    assert enrolment.otpauth_uri.startswith("otpauth://totp/")
    assert "reader%40example.com" in enrolment.otpauth_uri
    assert "issuer=Lumia" in enrolment.otpauth_uri
    assert enrolment.secret == SECRET


def test_the_current_code_is_accepted_and_names_its_step() -> None:
    now = datetime.now(UTC)

    assert verify_totp_code(SECRET, _code_at(now)) == _step_at(now)


def test_a_wrong_code_is_refused() -> None:
    now = datetime.now(UTC)
    wrong = "000000" if _code_at(now) != "000000" else "111111"

    assert verify_totp_code(SECRET, wrong) is None


def test_a_code_from_the_previous_window_is_still_accepted() -> None:
    """Authenticator clocks drift, and six digits take a moment to read and type."""
    previous = datetime.now(UTC) - timedelta(seconds=STEP_SECONDS)

    assert verify_totp_code(SECRET, _code_at(previous)) == _step_at(previous)


def test_a_code_from_beyond_the_drift_window_is_refused() -> None:
    stale = datetime.now(UTC) - timedelta(seconds=STEP_SECONDS * (DRIFT_STEPS + 2))

    assert verify_totp_code(SECRET, _code_at(stale)) is None


def test_a_code_already_spent_cannot_be_replayed_within_its_window() -> None:
    now = datetime.now(UTC)
    code = _code_at(now)
    step = verify_totp_code(SECRET, code)
    assert step is not None

    assert verify_totp_code(SECRET, code, last_used_step=step) is None


def test_a_still_valid_earlier_code_cannot_walk_back_through_the_drift_window() -> None:
    now = datetime.now(UTC)
    previous = now - timedelta(seconds=STEP_SECONDS)

    assert verify_totp_code(SECRET, _code_at(previous), last_used_step=_step_at(now)) is None


def test_the_next_code_is_accepted_after_one_was_spent() -> None:
    now = datetime.now(UTC)
    spent_step = _step_at(now) - 1

    assert verify_totp_code(SECRET, _code_at(now), last_used_step=spent_step) == _step_at(now)


def test_anything_that_is_not_six_digits_is_refused() -> None:
    for candidate in ("", "12345", "1234567", "12345a", "١٢٣٤٥٦", " 123456"):
        assert verify_totp_code(SECRET, candidate) is None


def test_recovery_codes_come_in_a_full_set_and_are_all_different() -> None:
    codes = generate_recovery_codes()

    assert len(codes) == RECOVERY_CODE_COUNT
    assert len(set(codes)) == RECOVERY_CODE_COUNT


def test_a_recovery_code_is_grouped_so_it_can_be_read_off_paper() -> None:
    code = generate_recovery_codes(1)[0]

    assert code.count("-") == 4
    assert all(len(group) == 4 for group in code.split("-"))


def test_a_recovery_code_typed_without_its_dashes_still_matches() -> None:
    code = generate_recovery_codes(1)[0]

    assert normalise_recovery_code(code) == normalise_recovery_code(code.replace("-", ""))
    assert normalise_recovery_code(code.upper()) == normalise_recovery_code(code)


def test_every_candidate_step_is_compared_even_once_one_has_matched() -> None:
    """Returning early would leak through timing which step a code came from."""
    now = datetime.now(UTC)
    with patch("api.technical.auth.totp.hmac.compare_digest", wraps=lambda a, b: a == b) as compare:
        verify_totp_code(SECRET, _code_at(now))

    assert compare.call_count == DRIFT_STEPS * 2 + 1
