"""RFC 6238 one-time codes, and the single-use codes that stand in for a lost authenticator.

The algorithm itself comes from pyotp rather than from a local HMAC loop: a home-made
implementation is where the drift window, the counter arithmetic and the comparison quietly go
wrong, and none of those mistakes show up in a happy-path test.
"""

import hmac
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime

import pyotp

#: One step either side of the current one, the usual allowance for a clock that has drifted and
#: for a reader who types the six digits as the window turns. Wider would triple the guessing
#: surface for no practical gain.
DRIFT_STEPS = 1

CODE_DIGITS = 6
_DIGITS = frozenset("0123456789")

RECOVERY_CODE_COUNT = 10
#: Ten bytes, so eighty bits of entropy: far past what an offline search of the stored SHA-256
#: digests could reach, and still short enough to be read off paper.
_RECOVERY_CODE_BYTES = 10
_RECOVERY_GROUP_SIZE = 4


@dataclass(frozen=True)
class TotpEnrolment:
    """What an authenticator needs to be set up: the QR payload, and the same secret to type."""

    secret: str
    otpauth_uri: str


def generate_totp_secret() -> str:
    return pyotp.random_base32()


def build_enrolment(secret: str, *, account_name: str, issuer: str) -> TotpEnrolment:
    uri = pyotp.TOTP(secret).provisioning_uri(name=account_name, issuer_name=issuer)
    return TotpEnrolment(secret=secret, otpauth_uri=uri)


def verify_totp_code(secret: str, code: str, *, last_used_step: int | None = None) -> int | None:
    """Returns the time step `code` belongs to, or None when it is not a code for this secret.

    The step comes back rather than a bare boolean because a code stays valid for the whole of its
    window: without remembering which step was spent, anyone who reads the six digits over a
    shoulder can replay them for the next half-minute. A step at or below the last one accepted is
    therefore refused, which also rules out walking backwards through the drift allowance.
    """
    if len(code) != CODE_DIGITS or not _DIGITS.issuperset(code):
        return None

    totp = pyotp.TOTP(secret)
    current_step = totp.timecode(datetime.now(UTC))
    matched: int | None = None
    # Every candidate is compared, and the comparison itself is constant time: returning as soon as
    # one matches would leak through timing which step the code came from.
    for offset in range(-DRIFT_STEPS, DRIFT_STEPS + 1):
        step = current_step + offset
        if hmac.compare_digest(totp.generate_otp(step), code):
            matched = step

    if matched is None or (last_used_step is not None and matched <= last_used_step):
        return None
    return matched


def generate_recovery_codes(count: int = RECOVERY_CODE_COUNT) -> list[str]:
    return [_format_recovery_code(secrets.token_hex(_RECOVERY_CODE_BYTES)) for _ in range(count)]


def normalise_recovery_code(code: str) -> str:
    """Folds away the presentation, so a code typed without its dashes still matches."""
    return "".join(character for character in code.lower() if character in "0123456789abcdef")


def _format_recovery_code(raw: str) -> str:
    groups = [
        raw[index : index + _RECOVERY_GROUP_SIZE]
        for index in range(0, len(raw), _RECOVERY_GROUP_SIZE)
    ]
    return "-".join(groups)
