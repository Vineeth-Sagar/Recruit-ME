"""Outbound transactional email.

Phase 4.2 ships the console sender (logs the message) and a Resend HTTP sender.
The full templated report delivery is Phase 4.4; here it is just auth mail
(verify address, reset password).
"""

from __future__ import annotations

import logging
from typing import Protocol

import httpx

from ..config import Settings, get_settings

logger = logging.getLogger(__name__)


class EmailSender(Protocol):
    async def send(self, *, to: str, subject: str, html: str) -> None: ...


class ConsoleEmailSender:
    """Dev default — writes the email to the log instead of sending it."""

    def __init__(self) -> None:
        self.sent: list[dict[str, str]] = []

    async def send(self, *, to: str, subject: str, html: str) -> None:
        self.sent.append({"to": to, "subject": subject, "html": html})
        logger.info("[email:console] to=%s subject=%s\n%s", to, subject, html)


class ResendEmailSender:
    def __init__(self, api_key: str, sender: str) -> None:
        self._api_key = api_key
        self._sender = sender

    async def send(self, *, to: str, subject: str, html: str) -> None:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                "https://api.resend.com/emails",
                headers={"Authorization": f"Bearer {self._api_key}"},
                json={"from": self._sender, "to": [to], "subject": subject, "html": html},
            )
            resp.raise_for_status()


def build_email_sender(settings: Settings | None = None) -> EmailSender:
    settings = settings or get_settings()
    if settings.email_provider == "resend" and settings.resend_api_key:
        return ResendEmailSender(settings.resend_api_key, settings.email_from)
    return ConsoleEmailSender()
