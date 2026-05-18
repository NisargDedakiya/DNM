"""
Notification orchestration service.

Responsibilities:
- create notifications
- deliver notifications
- suppress duplicate notifications
- return historical notification records
"""
from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import and_, desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.redis import get_redis
from backend.models.notification import (
    Notification,
    NotificationChannel,
    NotificationSeverity,
    NotificationStatus,
    NotificationType,
)
from backend.models.team_member import TeamMember
from backend.models.user import User
from backend.services.discord_service import DiscordService
from backend.services.email_service import EmailService
from backend.services.slack_service import SlackService
from backend.websocket.pubsub import publish_event


class NotificationService:
    """Central notification service for secure, async alert delivery."""

    DEDUP_WINDOW_SECONDS = 900

    def __init__(self, db: AsyncSession):
        self.db = db
        self.email_service = EmailService()
        self.slack_service = SlackService()
        self.discord_service = DiscordService()

    def _sanitize_text(self, text: str, max_length: int = 2000) -> str:
        cleaned = (text or "").strip()

        # Redact obvious credential patterns.
        patterns = [
            r"(?i)bearer\s+[a-z0-9\-\._~\+\/]+=*",
            r"(?i)(api[_-]?key|token|secret|password)\s*[:=]\s*[^\s,;]+",
            r"(?i)authorization\s*[:=]\s*[^\s,;]+",
            r"(?i)cookie\s*[:=]\s*[^\s,;]+",
        ]
        for pattern in patterns:
            cleaned = re.sub(pattern, "[REDACTED]", cleaned)

        return cleaned[:max_length]

    def _sanitize_payload(self, payload: Any) -> Any:
        if isinstance(payload, dict):
            safe: dict[str, Any] = {}
            for key, value in payload.items():
                key_str = str(key)
                if re.search(r"(?i)(secret|token|password|api[_-]?key|authorization|cookie)", key_str):
                    safe[key_str] = "[REDACTED]"
                    continue
                safe[key_str] = self._sanitize_payload(value)
            return safe

        if isinstance(payload, list):
            return [self._sanitize_payload(item) for item in payload[:100]]

        if isinstance(payload, str):
            return self._sanitize_text(payload, max_length=1200)

        return payload

    def _build_dedup_key(
        self,
        organization_id: UUID,
        notification_type: str,
        severity: str,
        title: str,
        message: str,
        channel: str,
    ) -> str:
        raw = f"{organization_id}:{notification_type}:{severity}:{title}:{message}:{channel}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:64]

    async def suppress_duplicate_notifications(
        self,
        organization_id: UUID,
        dedup_key: str,
        channel: str,
        dedup_window_seconds: int | None = None,
    ) -> bool:
        """Return True if a similar recent notification already exists."""
        window = dedup_window_seconds or self.DEDUP_WINDOW_SECONDS
        cutoff = datetime.now(timezone.utc) - timedelta(seconds=window)

        result = await self.db.execute(
            select(Notification.id).where(
                and_(
                    Notification.organization_id == organization_id,
                    Notification.dedup_key == dedup_key,
                    Notification.channel == channel,
                    Notification.created_at >= cutoff,
                    Notification.status.in_(
                        [
                            NotificationStatus.PENDING,
                            NotificationStatus.DELIVERED,
                            NotificationStatus.SUPPRESSED,
                        ]
                    ),
                )
            )
        )
        return result.first() is not None

    async def create_notification(
        self,
        organization_id: UUID,
        notification_type: str,
        severity: str,
        title: str,
        message: str,
        channel: str,
        metadata: dict[str, Any] | None = None,
        dedup_window_seconds: int | None = None,
    ) -> Notification:
        """Create a notification row with sanitization and dedupe suppression state."""
        safe_title = self._sanitize_text(title, max_length=255)
        safe_message = self._sanitize_text(message, max_length=4000)
        safe_metadata = self._sanitize_payload(metadata or {})

        dedup_key = self._build_dedup_key(
            organization_id=organization_id,
            notification_type=notification_type,
            severity=severity,
            title=safe_title,
            message=safe_message,
            channel=channel,
        )

        is_duplicate = await self.suppress_duplicate_notifications(
            organization_id=organization_id,
            dedup_key=dedup_key,
            channel=channel,
            dedup_window_seconds=dedup_window_seconds,
        )

        notification = Notification(
            organization_id=organization_id,
            notification_type=NotificationType(notification_type),
            severity=NotificationSeverity(severity),
            title=safe_title,
            message=safe_message,
            channel=NotificationChannel(channel),
            status=NotificationStatus.SUPPRESSED if is_duplicate else NotificationStatus.PENDING,
            dedup_key=dedup_key,
            notification_metadata=safe_metadata,
        )

        self.db.add(notification)
        await self.db.commit()
        await self.db.refresh(notification)
        return notification

    async def _broadcast_websocket_notification(self, organization_id: UUID, payload: dict[str, Any]) -> dict[str, Any]:
        """Publish notification event to all active org members via user channels."""
        result = await self.db.execute(
            select(TeamMember.user_id).where(
                and_(
                    TeamMember.organization_id == organization_id,
                    TeamMember.is_active == True,
                )
            )
        )
        user_ids = [str(row[0]) for row in result.all()]

        delivered = 0
        for user_id in user_ids:
            await publish_event(
                user_id=user_id,
                event={
                    "event": "notification",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "payload": payload,
                },
            )
            delivered += 1

        return {"success": True, "fanout": delivered}

    async def _list_org_member_emails(self, organization_id: UUID) -> list[str]:
        result = await self.db.execute(
            select(User.email)
            .join(TeamMember, TeamMember.user_id == User.id)
            .where(
                and_(
                    TeamMember.organization_id == organization_id,
                    TeamMember.is_active == True,
                    User.is_active == True,
                )
            )
        )
        return [row[0] for row in result.all()]

    async def send_notification(
        self,
        notification: Notification,
        channel_config: dict[str, Any] | None = None,
    ) -> Notification:
        """Deliver pending notification and update delivery state."""
        if notification.status == NotificationStatus.SUPPRESSED:
            return notification

        channel_config = channel_config or {}
        notification.delivery_attempts += 1
        notification.last_attempt_at = datetime.now(timezone.utc)

        result: dict[str, Any] = {"success": False, "error": "Unsupported channel"}

        payload = {
            "id": str(notification.id),
            "organization_id": str(notification.organization_id),
            "notification_type": notification.notification_type,
            "severity": notification.severity,
            "title": notification.title,
            "message": notification.message,
            "channel": notification.channel,
            "status": notification.status,
            "created_at": notification.created_at.isoformat() if notification.created_at else None,
            "metadata": notification.notification_metadata or {},
        }

        if notification.channel == NotificationChannel.WEBSOCKET:
            result = await self._broadcast_websocket_notification(notification.organization_id, payload)

        elif notification.channel == NotificationChannel.EMAIL:
            recipients = channel_config.get("emails") or await self._list_org_member_emails(notification.organization_id)
            result = await self.email_service.send_email_alert(
                recipients=recipients,
                subject=notification.title,
                message=notification.message,
                severity=str(notification.severity),
            )

        elif notification.channel == NotificationChannel.SLACK:
            webhook_url = channel_config.get("slack_webhook_url", "")
            if webhook_url:
                result = await self.slack_service.send_slack_alert(
                    webhook_url=webhook_url,
                    title=notification.title,
                    message=notification.message,
                    severity=str(notification.severity),
                    metadata=notification.notification_metadata or {},
                )
            else:
                result = {"success": False, "error": "Missing Slack webhook URL"}

        elif notification.channel == NotificationChannel.DISCORD:
            webhook_url = channel_config.get("discord_webhook_url", "")
            if webhook_url:
                result = await self.discord_service.send_discord_alert(
                    webhook_url=webhook_url,
                    title=notification.title,
                    message=notification.message,
                    severity=str(notification.severity),
                    metadata=notification.notification_metadata or {},
                )
            else:
                result = {"success": False, "error": "Missing Discord webhook URL"}

        if result.get("success"):
            notification.status = NotificationStatus.DELIVERED
            notification.delivered_at = datetime.now(timezone.utc)
            notification.error_message = None
        else:
            notification.status = NotificationStatus.FAILED
            notification.error_message = str(result.get("error", "Unknown delivery failure"))[:2000]

        await self.db.commit()
        await self.db.refresh(notification)
        return notification

    async def get_notification_history(
        self,
        organization_id: UUID,
        limit: int = 100,
        offset: int = 0,
        channel: str | None = None,
        severity: str | None = None,
        status: str | None = None,
    ) -> list[Notification]:
        """Fetch organization-scoped notification history with optional filters."""
        query = select(Notification).where(Notification.organization_id == organization_id)

        if channel:
            query = query.where(Notification.channel == channel)
        if severity:
            query = query.where(Notification.severity == severity)
        if status:
            query = query.where(Notification.status == status)

        query = query.order_by(desc(Notification.created_at)).offset(offset).limit(max(1, min(limit, 500)))

        result = await self.db.execute(query)
        return result.scalars().all()

    async def get_preferences(self, organization_id: UUID) -> dict[str, Any]:
        """Read routing preferences from Redis with sane defaults."""
        defaults: dict[str, Any] = {
            "severity_channels": {
                "critical": ["websocket", "slack", "discord", "email"],
                "high": ["websocket", "slack", "email"],
                "medium": ["websocket", "slack"],
                "low": ["websocket"],
                "info": ["websocket"],
            },
            "slack_webhook_url": "",
            "discord_webhook_url": "",
            "emails": [],
            "rate_limit_per_minute": {
                "critical": 60,
                "high": 30,
                "medium": 15,
                "low": 10,
                "info": 10,
            },
        }

        try:
            redis = await get_redis()
            raw = await redis.get(f"notification:preferences:{organization_id}")
            if not raw:
                return defaults

            try:
                parsed = json.loads(raw)
                return {**defaults, **parsed}
            except Exception:
                return defaults
        except Exception:
            return defaults

    async def update_preferences(self, organization_id: UUID, preferences: dict[str, Any]) -> dict[str, Any]:
        """Store organization notification routing preferences in Redis."""
        safe_prefs = self._sanitize_payload(preferences)
        try:
            redis = await get_redis()
            await redis.set(f"notification:preferences:{organization_id}", json.dumps(safe_prefs))
        except Exception:
            # Keep API behavior stable even if Redis is temporarily unavailable.
            pass
        return safe_prefs
