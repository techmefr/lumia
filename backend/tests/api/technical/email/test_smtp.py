from unittest.mock import AsyncMock, patch

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
