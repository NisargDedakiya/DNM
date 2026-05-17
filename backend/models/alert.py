"""
Alert model for monitoring-driven notifications.
Tracks real-time alerts from continuous monitoring with deduplication support.
"""
from enum import Enum
from uuid import UUID

from sqlalchemy import ForeignKey, Index, String, Boolean, DateTime, Enum as SQLEnum, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime

from backend.database.base import BaseModel


class AlertType(str, Enum):
    """Alert classification."""

    NEW_ASSET = "new_asset"
    NEW_FINDING = "new_finding"
    NEW_ENDPOINT = "new_endpoint"
    ASSET_REMOVED = "asset_removed"
    FINDING_UPDATED = "finding_updated"
    SCAN_COMPLETED = "scan_completed"
    SCAN_FAILED = "scan_failed"


class AlertSeverity(str, Enum):
    """Alert severity levels."""

    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class Alert(BaseModel):
    """
    Real-time alert from monitoring system.
    
    Alerts notify users of significant events discovered during continuous
    monitoring, with deduplication to prevent alert storms.
    """

    __tablename__ = "alerts"

    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    
    program_id: Mapped[UUID] = mapped_column(
        ForeignKey("programs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    
    monitoring_rule_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("monitoring_rules.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    
    scan_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("scans.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    
    alert_type: Mapped[str] = mapped_column(
        SQLEnum(AlertType, name="alert_type_enum"),
        nullable=False,
        index=True,
    )
    
    severity: Mapped[str] = mapped_column(
        SQLEnum(AlertSeverity, name="alert_severity_enum"),
        nullable=False,
        default=AlertSeverity.MEDIUM,
        index=True,
    )
    
    title: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    
    description: Mapped[str] = mapped_column(Text, nullable=False)
    
    # Delta identification
    delta_data: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    # Duplicate tracking
    is_duplicate: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        index=True,
    )
    
    parent_alert_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("alerts.id", ondelete="CASCADE"),
        nullable=True,
    )
    
    # Status tracking
    is_acknowledged: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        index=True,
    )
    
    acknowledged_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    
    acknowledged_by_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Relationships
    organization = relationship("Organization", foreign_keys=[organization_id])
    program = relationship("Program", foreign_keys=[program_id])
    monitoring_rule = relationship("MonitoringRule", foreign_keys=[monitoring_rule_id])
    scan = relationship("Scan", foreign_keys=[scan_id])
    acknowledged_by = relationship("User", foreign_keys=[acknowledged_by_id])

    __table_args__ = (
        Index("ix_alerts_org_prog", "organization_id", "program_id"),
        Index("ix_alerts_type_severity", "alert_type", "severity"),
        Index("ix_alerts_unacknowledged", "is_acknowledged"),
    )
