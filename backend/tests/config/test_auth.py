import pytest
from pydantic import ValidationError

from config.auth import AuthConfig


@pytest.mark.parametrize("placeholder", ["change-me", "CHANGE-ME", "changeme", " ", ""])
def test_placeholder_jwt_secret_is_refused(
    monkeypatch: pytest.MonkeyPatch, placeholder: str
) -> None:
    monkeypatch.setenv("JWT_SECRET", placeholder)
    with pytest.raises(ValidationError):
        AuthConfig()


def test_generated_jwt_secret_is_accepted(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("JWT_SECRET", "k3J9xV2mQ8wZr5Tn7YbL1cHd4PfGs6Aa")
    assert AuthConfig().jwt_secret == "k3J9xV2mQ8wZr5Tn7YbL1cHd4PfGs6Aa"
