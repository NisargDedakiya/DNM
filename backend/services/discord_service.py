"""
Discord webhook notification service with embed formatting.
"""
from __future__ import annotations

from typing import Any
from urllib.parse import urlparse

import httpx


class DiscordService:
    """Discord webhook client with URL allow-list and embed payloads."""

    ALLOWED_HOSTS = {"discord.com", "discordapp.com", "canary.discord.com"}

    def _is_safe_webhook(self, webhook_url: str) -> bool:
        try:
            parsed = urlparse(webhook_url)
            return parsed.scheme == "https" and parsed.hostname in self.ALLOWED_HOSTS
        except Exception:
            return False

    def _severity_color(self, severity: str) -> int:
        return {
            "critical": 0xFF0000,
            "high": 0xFF6B00,
            "medium": 0xFFC400,
            "low": 0x2D9CDB,
            "info": 0x5865F2,
        }.get(severity.lower(), 0x5865F2)

    def format_discord_embed(
        self,
        title: str,
        message: str,
        severity: str,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Create a Discord embed payload for realtime alerts."""
        fields = []
        if metadata:
            for key, value in list(metadata.items())[:8]:
                fields.append(
                    {
                        "name": str(key)[:180],
                        "value": str(value)[:500] or "-",
                        "inline": False,
                    }
                )

        embed = {
            "title": f"[{severity.upper()}] {title[:180]}",
            "description": message[:3500],
            "color": self._severity_color(severity),
            "fields": fields,
        }
        return {"embeds": [embed]}

    async def send_discord_alert(
        self,
        webhook_url: str,
        title: str,
        message: str,
        severity: str,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Send a Discord webhook alert."""
        if not self._is_safe_webhook(webhook_url):
            return {"success": False, "error": "Unsafe or invalid Discord webhook URL"}

        payload = self.format_discord_embed(title=title, message=message, severity=severity, metadata=metadata)
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(webhook_url, json=payload)
            if response.status_code >= 400:
                return {
                    "success": False,
                    "error": f"Discord webhook failed with status {response.status_code}",
                }

        return {"success": True}
