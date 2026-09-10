import logging
from email.message import EmailMessage

import aiosmtplib

from api.technical.logging.external import describe_error, log_external_failure
from config.email import get_email_config

SERVICE_NAME = "smtp"

logger = logging.getLogger(__name__)


async def send_email(*, to: str, subject: str, body: str) -> None:
    config = get_email_config()
    message = EmailMessage()
    message["From"] = config.smtp_from_address
    message["To"] = to
    message["Subject"] = subject
    message.set_content(body)

    try:
        await aiosmtplib.send(
            message,
            hostname=config.smtp_host,
            port=config.smtp_port,
            username=config.smtp_username,
            password=config.smtp_password,
            start_tls=config.smtp_use_tls,
        )
    except (aiosmtplib.SMTPException, OSError) as exc:
        # The recipient is deliberately absent from the log line: a failed magic link is not worth
        # writing a reader's address into the instance logs.
        log_external_failure(
            logger,
            service=SERVICE_NAME,
            operation="send",
            url=f"smtp://{config.smtp_host}:{config.smtp_port}",
            error=describe_error(exc),
        )
        raise
