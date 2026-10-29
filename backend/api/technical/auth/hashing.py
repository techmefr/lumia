from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

_hasher = PasswordHasher()


_DECOY_HASH = _hasher.hash("decoy-password-never-matched")


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return _hasher.verify(password_hash, password)
    except VerifyMismatchError:
        return False


def spend_verification_time(password: str) -> None:
    verify_password(password, _DECOY_HASH)
