import pytest
from pydantic import ValidationError

from config.miniflux import MinifluxConfig


def _environment(monkeypatch: pytest.MonkeyPatch, *, password: str, secret: str) -> None:
    monkeypatch.setenv("MINIFLUX_BASE_URL", "http://miniflux.test")
    monkeypatch.setenv("MINIFLUX_USERNAME", "admin")
    monkeypatch.setenv("MINIFLUX_PASSWORD", password)
    monkeypatch.setenv("MINIFLUX_WEBHOOK_SECRET", secret)


@pytest.mark.parametrize("placeholder", ["change-me", "CHANGE-ME", "changeme", " ", ""])
def test_placeholder_miniflux_password_is_refused(
    monkeypatch: pytest.MonkeyPatch, placeholder: str
) -> None:
    _environment(monkeypatch, password=placeholder, secret="k3J9xV2mQ8wZr5Tn7YbL1cHd4PfGs6Aa")
    with pytest.raises(ValidationError):
        MinifluxConfig()


@pytest.mark.parametrize("placeholder", ["change-me", "CHANGE-ME", "changeme", " ", ""])
def test_placeholder_webhook_secret_is_refused(
    monkeypatch: pytest.MonkeyPatch, placeholder: str
) -> None:
    _environment(monkeypatch, password="k3J9xV2mQ8wZr5Tn7YbL1cHd4PfGs6Aa", secret=placeholder)
    with pytest.raises(ValidationError):
        MinifluxConfig()


def test_generated_values_are_accepted(monkeypatch: pytest.MonkeyPatch) -> None:
    _environment(monkeypatch, password="pw-Zr5Tn7YbL1cHd4", secret="sec-Zr5Tn7YbL1cHd4")
    config = MinifluxConfig()
    assert config.miniflux_password == "pw-Zr5Tn7YbL1cHd4"
    assert config.miniflux_webhook_secret == "sec-Zr5Tn7YbL1cHd4"
