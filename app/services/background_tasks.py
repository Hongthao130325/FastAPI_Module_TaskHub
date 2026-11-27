import asyncio
import logging
import smtplib
import ssl
from email.message import EmailMessage

from app.core.config import settings

logger = logging.getLogger(__name__)


def log_comment_created(
    *,
    comment_id: int,
    task_id: int,
    author_id: int,
) -> None:
    logger.info(
        "Comment %s created for task %s by user %s",
        comment_id,
        task_id,
        author_id,
    )


def _send_task_assigned_email(
    *,
    to_email: str,
    recipient_name: str,
    task_title: str,
    task_id: int,
) -> None:
    if not settings.SMTP_HOST or not settings.SMTP_FROM_EMAIL:
        logger.warning("Task assignment email skipped: SMTP is not configured")
        return

    message = EmailMessage()
    message["Subject"] = f"You have been assigned to task #{task_id}"
    message["From"] = settings.SMTP_FROM_EMAIL
    message["To"] = to_email
    message.set_content(
        f"Hello {recipient_name},\n\n"
        f"You have been assigned to the following task:\n"
        f"Task ID: {task_id}\n"
        f"Title: {task_title}\n\n"
        "Please sign in to TaskHub to view the task details."
    )

    with smtplib.SMTP(
        settings.SMTP_HOST,
        settings.SMTP_PORT,
        timeout=settings.SMTP_TIMEOUT_SECONDS,
    ) as server:
        if settings.SMTP_USE_TLS:
            server.starttls(context=ssl.create_default_context())

        if settings.SMTP_USERNAME and settings.SMTP_PASSWORD:
            server.login(
                settings.SMTP_USERNAME,
                settings.SMTP_PASSWORD.get_secret_value(),
            )

        server.send_message(message)


async def send_task_assigned_email(
    *,
    to_email: str,
    recipient_name: str,
    task_title: str,
    task_id: int,
) -> None:
    try:
        await asyncio.to_thread(
            _send_task_assigned_email,
            to_email=to_email,
            recipient_name=recipient_name,
            task_title=task_title,
            task_id=task_id,
        )
    except Exception:
        logger.exception(
            "Failed to send task assignment email for task %s",
            task_id,
        )
