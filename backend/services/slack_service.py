"""
Slack webhook notification service with structured message formatting.
"""
from __future__ import annotations

from typing import Any
from urllib.parse import urlparse

import httpx


class SlackService:
    """Slack webhook client with strict URL validation."""

    ALLOWED_HOSTS = {"hooks.slack.com"}

    def _is_safe_webhook(self, webhook_url: str) -> bool:
        try:
            parsed = urlparse(webhook_url)
            return parsed.scheme == "https" and parsed.hostname in self.ALLOWED_HOSTS
        except Exception:
            return False

    def _severity_emoji(self, severity: str) -> str:
        return {
            "critical": ":rotating_light:",
            "high": ":warning:",
            "medium": ":large_orange_diamond:",
            "low": ":large_blue_diamond:",
            "info": ":information_source:",
        }.get(severity.lower(), ":information_source:")

    def format_slack_message(
        self,
        title: str,
        message: str,
        severity: str,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Build a structured Slack payload."""
        meta_lines = []
        if metadata:
            for key, value in metadata.items():
                meta_lines.append(f"*{str(key)[:40]}:* {str(value)[:200]}")

        text = f"{self._severity_emoji(severity)} [{severity.upper()}] {title[:180]}"
        blocks: list[dict[str, Any]] = [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": text,
                },
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": message[:2800],
                },
            },
        ]

        if meta_lines:
            blocks.append(
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": "\n".join(meta_lines[:10]),
                    },
                }
            )

        return {"text": text, "blocks": blocks}

    async def send_slack_alert(
        self,
        webhook_url: str,
        title: str,
        message: str,
        severity: str,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Deliver a structured Slack webhook alert."""
        if not self._is_safe_webhook(webhook_url):
            return {"success": False, "error": "Unsafe or invalid Slack webhook URL"}

        payload = self.format_slack_message(title=title, message=message, severity=severity, metadata=metadata)
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(webhook_url, json=payload)
            if response.status_code >= 400:
                return {
                    "success": False,
                    "error": f"Slack webhook failed with status {response.status_code}",
                }

        return {"success": True}
