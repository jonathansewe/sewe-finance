"""The email service picks the right sender and calls Resend correctly."""

from typing import Any

import pytest

from app.services import email


def test_console_is_the_default(capsys: pytest.CaptureFixture[str]) -> None:
    sender = email.get_email_sender()
    assert isinstance(sender, email.ConsoleEmailSender)
    sender.send("jo@example.com", "Your code", "Code: 123456")
    assert "Code: 123456" in capsys.readouterr().out


def test_resend_sender_is_chosen_by_env_and_sends_from_finance(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.config import get_settings

    monkeypatch.setenv("EMAIL_PROVIDER", "resend")
    monkeypatch.setenv("RESEND_API_KEY", "re_test_placeholder")
    get_settings.cache_clear()
    sent: list[dict[str, Any]] = []
    monkeypatch.setattr(email.resend.Emails, "send", lambda params: sent.append(params))

    sender = email.get_email_sender()
    assert isinstance(sender, email.ResendEmailSender)
    sender.send("jo@example.com", "Your code", "Code: 123456")

    assert sent == [
        {
            "from": "SEWE Finance <finance@jonathansewe.com>",
            "to": ["jo@example.com"],
            "subject": "Your code",
            "text": "Code: 123456",
        }
    ]
    assert email.resend.api_key == "re_test_placeholder"
