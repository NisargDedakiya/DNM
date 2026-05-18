"""
Notification model for cross-channel security alert delivery.

Stores immutable notification events with delivery state, deduplication keys,
and organization isolation for audit-safe historical tracking.
"""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from uuid import UUID

from sqlalchemy import DateTime, Enum as SQLEnum, ForeignKey, Index, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database.base import BaseModel


class NotificationType(str, Enum):
    """Supported notification event categories."""

    NEW_FINDING = "new_finding"
    EXPOSURE_DETECTED = "exposure_detected"
    MONITORING_ALERT = "monitoring_alert"
    SCOPE_CHANGE = "scope_change"
    RISK_ESCALATION = "risk_escalation"


class NotificationChannel(str, Enum):
    """Outbound notification channels."""

    WEBSOCKET = "websocket"
    EMAIL = "email"
    SLACK = "slack"
    DISCORD = "discord"


class NotificationSeverity(str, Enum):
    """Notification severity levels for routing and escalation."""

    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class NotificationStatus(str, Enum):
    """Delivery lifecycle for a notification row."""

    PENDING = "pending"
    DELIVERED = "delivered"
    FAILED = "failed"
    SUPPRESSED = "suppressed"


class Notification(BaseModel):
    """
    Organization-scoped notification with delivery tracking metadata.

    Required business columns:
    - id, organization_id, notification_type, severity, title, message
    - channel, status, created_at
    """

    __tablename__ = "notifications"

    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    notification_type: Mapped[str] = mapped_column(
        SQLEnum(NotificationType, name="notification_type_enum"),
        nullable=False,
        index=True,
    )

    severity: Mapped[str] = mapped_column(
        SQLEnum(NotificationSeverity, name="notification_severity_enum"),
        nullable=False,
        index=True,
    )

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)

    channel: Mapped[str] = mapped_column(
        SQLEnum(NotificationChannel, name="notification_channel_enum"),
        nullable=False,
        index=True,
    )

    status: Mapped[str] = mapped_column(
        SQLEnum(NotificationStatus, name="notification_status_enum"),
        nullable=False,
        default=NotificationStatus.PENDING,
        index=True,
    )

    dedup_key: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    delivery_attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    last_attempt_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    notification_metadata: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    organization = relationship("Organization", foreign_keys=[organization_id], lazy="select")

    __table_args__ = (
        Index("ix_notifications_org_created", "organization_id", "created_at"),
        Index("ix_notifications_org_status", "organization_id", "status"),
        Index("ix_notifications_org_severity", "organization_id", "severity"),
        Index("ix_notifications_org_dedup", "organization_id", "dedup_key"),
    )
