import logging
from unittest.mock import AsyncMock, patch

import aiosmtplib
import pytest

from api.technical.email.smtp import send_email


async def test_send_email_calls_aiosmtplib_with_the_configured_credentials() -> None:
    with patch("api.technical.email.smtp.aiosmtplib.send", new_callable=AsyncMock) as mock_send:
        await send_email(to="user@example.com", subject="Hello", body="World")

    assert mock_send.await_args is not None
    args, kwargs = mock_send.await_args
    message = args[0]
    assert message["To"] == "user@example.com"
    assert message["Subject"] == "Hello"
    assert kwargs["hostname"] == "localhost"
    assert kwargs["username"] == "test"


async def test_send_email_logs_the_server_but_not_the_recipient_when_it_fails(
    caplog: pytest.LogCaptureFixture,
) -> None:
    failing_send = AsyncMock(side_effect=aiosmtplib.SMTPConnectError("connection refused"))
    with (
        patch("api.technical.email.smtp.aiosmtplib.send", failing_send),
        caplog.at_level(logging.WARNING),
        pytest.raises(aiosmtplib.SMTPConnectError),
    ):
        await send_email(to="reader@example.com", subject="Hello", body="World")

    record = caplog.records[-1]
    assert record.service == "smtp"  # type: ignore[attr-defined]
    assert record.url == "smtp://localhost:587"  # type: ignore[attr-defined]
    assert "SMTPConnectError" in record.error  # type: ignore[attr-defined]
    assert "reader@example.com" not in caplog.text
