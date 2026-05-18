"""
Severity-aware alert routing service.

Routes security events to configured channels with policy checks,
organizational preferences, and escalation behavior.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from backend.core.redis import get_redis
from backend.models.notification import Notification, NotificationSeverity, NotificationType
from backend.services.notification_service import NotificationService


class AlertRouterService:
    """Policy-aware alert routing across notification channels."""

    def __init__(self, notification_service: NotificationService):
        self.notification_service = notification_service

    async def determine_channels(
        self,
        organization_id: UUID,
        severity: str,
        notification_type: str,
    ) -> list[str]:
        """Determine destination channels using organization preferences."""
        prefs = await self.notification_service.get_preferences(organization_id)
        severity_channels = prefs.get("severity_channels", {})

        channels = severity_channels.get(severity.lower()) or ["websocket"]

        # Conservative default: always keep websocket for operational awareness.
        if "websocket" not in channels:
            channels = ["websocket", *channels]

        # Risk escalation always reaches external channels if configured.
        if notification_type == NotificationType.RISK_ESCALATION.value:
            for candidate in ["slack", "discord", "email"]:
                if candidate not in channels:
                    channels.append(candidate)

        # Remove duplicates while preserving order.
        return list(dict.fromkeys(channels))

    async def apply_alert_policies(
        self,
        organization_id: UUID,
        severity: str,
        notification_type: str,
    ) -> dict[str, Any]:
        """Apply throttling and escalation policies before dispatch."""
        prefs = await self.notification_service.get_preferences(organization_id)
        limits = prefs.get("rate_limit_per_minute", {})
        limit = int(limits.get(severity.lower(), 10))

        count = 1
        try:
            redis = await get_redis()
            now = datetime.now(timezone.utc)
            minute_bucket = now.strftime("%Y%m%d%H%M")
            throttle_key = f"notification:throttle:{organization_id}:{severity}:{minute_bucket}"

            count = await redis.incr(throttle_key)
            if count == 1:
                await redis.expire(throttle_key, 70)
        except Exception:
            # Fail-open to preserve incident visibility if Redis is unavailable.
            count = 1

        throttled = count > limit

        escalation = severity.lower() in {NotificationSeverity.CRITICAL.value, NotificationSeverity.HIGH.value}
        if notification_type == NotificationType.RISK_ESCALATION.value:
            escalation = True

        return {
            "throttled": throttled,
            "escalation": escalation,
            "throttle_count": count,
            "throttle_limit": limit,
        }

    async def route_alert(
        self,
        organization_id: UUID,
        notification_type: str,
        severity: str,
        title: str,
        message: str,
        metadata: dict[str, Any] | None = None,
    ) -> list[Notification]:
        """Route alert to selected channels and return created notifications."""
        policy = await self.apply_alert_policies(
            organization_id=organization_id,
            severity=severity,
            notification_type=notification_type,
        )

        # Prevent low-value alert storms while preserving high severity delivery.
        if policy["throttled"] and severity.lower() in {"info", "low", "medium"}:
            suppressed = await self.notification_service.create_notification(
                organization_id=organization_id,
                notification_type=notification_type,
                severity=severity,
                title=title,
                message=message,
                channel="websocket",
                metadata={
                    "suppression_reason": "rate_limited",
                    "policy": policy,
                    "source": metadata or {},
                },
                dedup_window_seconds=60,
            )
            return [suppressed]

        channels = await self.determine_channels(
            organization_id=organization_id,
            severity=severity,
            notification_type=notification_type,
        )
        prefs = await self.notification_service.get_preferences(organization_id)

        routed: list[Notification] = []
        for channel in channels:
            notification = await self.notification_service.create_notification(
                organization_id=organization_id,
                notification_type=notification_type,
                severity=severity,
                title=title,
                message=message,
                channel=channel,
                metadata={
                    "routing": {
                        "policy": policy,
                        "notification_type": notification_type,
                        "channel": channel,
                    },
                    "source": metadata or {},
                },
            )

            delivered = await self.notification_service.send_notification(
                notification,
                channel_config={
                    "slack_webhook_url": prefs.get("slack_webhook_url", ""),
                    "discord_webhook_url": prefs.get("discord_webhook_url", ""),
                    "emails": prefs.get("emails", []),
                },
            )
            routed.append(delivered)

        return routed
