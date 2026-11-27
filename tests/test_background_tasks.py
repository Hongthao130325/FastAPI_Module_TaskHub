from unittest.mock import MagicMock

import pytest

from app.services import background_tasks


@pytest.mark.asyncio
async def test_task_assignment_email_skips_when_smtp_is_not_configured(
    monkeypatch,
    caplog,
):
    monkeypatch.setattr(background_tasks.settings, "SMTP_HOST", None)
    monkeypatch.setattr(background_tasks.settings, "SMTP_FROM_EMAIL", None)

    await background_tasks.send_task_assigned_email(
        to_email="assignee@example.com",
        recipient_name="Test Assignee",
        task_title="Test Task",
        task_id=1,
    )

    assert "SMTP is not configured" in caplog.text


@pytest.mark.asyncio
async def test_task_assignment_email_sends_message(
    monkeypatch,
):
    monkeypatch.setattr(background_tasks.settings, "SMTP_HOST", "smtp.example.com")
    monkeypatch.setattr(background_tasks.settings, "SMTP_PORT", 587)
    monkeypatch.setattr(
        background_tasks.settings, "SMTP_FROM_EMAIL", "noreply@example.com"
    )
    monkeypatch.setattr(background_tasks.settings, "SMTP_USE_TLS", False)
    monkeypatch.setattr(background_tasks.settings, "SMTP_USERNAME", None)
    monkeypatch.setattr(background_tasks.settings, "SMTP_PASSWORD", None)

    smtp_client = MagicMock()
    smtp_client.__enter__.return_value = smtp_client

    monkeypatch.setattr(
        background_tasks.smtplib,
        "SMTP",
        lambda *args, **kwargs: smtp_client,
    )

    await background_tasks.send_task_assigned_email(
        to_email="assignee@example.com",
        recipient_name="Test Assignee",
        task_title="Test Task",
        task_id=42,
    )

    smtp_client.send_message.assert_called_once()
    message = smtp_client.send_message.call_args.args[0]

    assert message["Subject"] == "You have been assigned to task #42"
    assert message["From"] == "noreply@example.com"
    assert message["To"] == "assignee@example.com"
    assert "Hello Test Assignee" in message.get_content()
    assert "Title: Test Task" in message.get_content()


@pytest.mark.asyncio
async def test_task_assignment_email_failure_is_logged(
    monkeypatch,
    caplog,
):
    def raise_smtp_error(**kwargs):
        raise RuntimeError("SMTP connection failed")

    monkeypatch.setattr(
        background_tasks,
        "_send_task_assigned_email",
        raise_smtp_error,
    )

    await background_tasks.send_task_assigned_email(
        to_email="assignee@example.com",
        recipient_name="Test Assignee",
        task_title="Test Task",
        task_id=99,
    )

    assert "Failed to send task assignment email for task 99" in caplog.text
    assert "SMTP connection failed" in caplog.text
