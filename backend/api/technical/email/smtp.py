from email.message import EmailMessage

import aiosmtplib

from config.email import get_email_config


async def send_email(*, to: str, subject: str, body: str, html_body: str | None = None) -> None:
    config = get_email_config()
    message = EmailMessage()
    message["From"] = config.smtp_from_address
    message["To"] = to
    message["Subject"] = subject
    message.set_content(body)
    if html_body is not None:
        message.add_alternative(html_body, subtype="html")

    await aiosmtplib.send(
        message,
        hostname=config.smtp_host,
        port=config.smtp_port,
        username=config.smtp_username,
        password=config.smtp_password,
        start_tls=config.smtp_use_tls,
    )
