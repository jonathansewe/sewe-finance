"""Sending email behind one small interface (D-25).

Routers call `sender.send(...)` and never know which vendor is behind it.
`ConsoleEmailSender` (local dev, CI) logs the message instead of sending,
so no real key is needed and no real mail goes out. `ResendEmailSender`
is production, from finance@jonathansewe.com (Q16). Adding Amazon SES
later means one new class here and one new EMAIL_PROVIDER value.
"""

import logging
from functools import lru_cache
from typing import Protocol

import resend

from app.config import get_settings

log = logging.getLogger("sewe.email")


class EmailSender(Protocol):
    def send(self, to: str, subject: str, text: str, html: str | None = None) -> None: ...


class ConsoleEmailSender:
    """Prints the email to the API log. Local development only: it shows the code."""

    def send(self, to: str, subject: str, text: str, html: str | None = None) -> None:
        # The one deliberate exception to "never log codes": this sender
        # exists so a developer can read the code. Production uses Resend.
        print(f"\n--- email to {to} ---\nSubject: {subject}\n\n{text}\n--- end email ---\n")


class ResendEmailSender:
    def __init__(self, api_key: str, from_address: str) -> None:
        self._api_key = api_key
        self._from = from_address

    def send(self, to: str, subject: str, text: str, html: str | None = None) -> None:
        resend.api_key = self._api_key
        params: resend.Emails.SendParams = {
            "from": self._from,
            "to": [to],
            "subject": subject,
            "text": text,
        }
        if html is not None:
            params["html"] = html
        resend.Emails.send(params)
        log.info("email.sent")  # event only: no address, no content


@lru_cache
def _sender_for(provider: str, api_key: str, from_address: str) -> EmailSender:
    if provider == "resend":
        return ResendEmailSender(api_key, from_address)
    return ConsoleEmailSender()


def get_email_sender() -> EmailSender:
    """FastAPI dependency. Tests override it with an in-memory outbox."""
    s = get_settings()
    return _sender_for(s.email_provider, s.resend_api_key, s.email_from)
