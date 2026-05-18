"""
Async email delivery service for security notifications.

Uses SMTP with retry support and plain-text templates to avoid unsafe HTML
rendering risks in downstream mail clients.
"""
from __future__ import annotations

import asyncio
import os
import smtplib
from email.message import EmailMessage
from typing import Any


class EmailService:
    """SMTP-backed async email sender with bounded retries."""

    MAX_RECIPIENTS = 25

    def __init__(self) -> None:
        self.smtp_host = os.getenv("SMTP_HOST", "")
        self.smtp_port = int(os.getenv("SMTP_PORT", "587"))
        self.smtp_username = os.getenv("SMTP_USERNAME", "")
        self.smtp_password = os.getenv("SMTP_PASSWORD", "")
        self.smtp_from = os.getenv("SMTP_FROM", "alerts@nisarghunter.ai")
        self.smtp_use_tls = os.getenv("SMTP_USE_TLS", "true").lower() == "true"

    def _is_configured(self) -> bool:
        return bool(self.smtp_host and self.smtp_from)

    async def send_email_alert(
        self,
        recipients: list[str],
        subject: str,
        message: str,
        severity: str,
        max_retries: int = 3,
    ) -> dict[str, Any]:
        """Send a notification email with retry and bounded recipient fan-out."""
        unique_recipients = sorted({r.strip().lower() for r in recipients if r and "@" in r})
        unique_recipients = unique_recipients[: self.MAX_RECIPIENTS]

        if not unique_recipients:
            return {"success": False, "error": "No valid recipients provided"}

        if not self._is_configured():
            return {"success": False, "error": "SMTP is not configured"}

        body = (
            "NisargHunter AI Security Notification\n"
            "================================\n\n"
            f"Severity: {severity.upper()}\n"
            f"Title: {subject}\n\n"
            f"{message.strip()}\n"
        )

        for attempt in range(max_retries):
            try:
                await asyncio.to_thread(
                    self._send_sync,
                    recipients=unique_recipients,
                    subject=subject,
                    body=body,
                )
                return {
                    "success": True,
                    "recipients": unique_recipients,
                    "attempts": attempt + 1,
                }
            except Exception as exc:
                if attempt == max_retries - 1:
                    return {
                        "success": False,
                        "error": str(exc),
                        "attempts": max_retries,
                    }
                await asyncio.sleep(min(2 ** attempt, 10))

        return {"success": False, "error": "Email retries exhausted"}

    async def send_executive_summary(
        self,
        recipients: list[str],
        summary_title: str,
        summary_lines: list[str],
        max_retries: int = 3,
    ) -> dict[str, Any]:
        """Send a lightweight executive summary email digest."""
        message = "\n".join(f"- {line}" for line in summary_lines)
        return await self.send_email_alert(
            recipients=recipients,
            subject=summary_title,
            message=message,
            severity="info",
            max_retries=max_retries,
        )

    def _send_sync(self, recipients: list[str], subject: str, body: str) -> None:
        msg = EmailMessage()
        msg["From"] = self.smtp_from
        msg["To"] = ", ".join(recipients)
        msg["Subject"] = subject[:180]
        msg.set_content(body[:4000])

        with smtplib.SMTP(self.smtp_host, self.smtp_port, timeout=15) as smtp:
            if self.smtp_use_tls:
                smtp.starttls()
            if self.smtp_username:
                smtp.login(self.smtp_username, self.smtp_password)
            smtp.send_message(msg)
