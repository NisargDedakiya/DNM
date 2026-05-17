"""
Monitoring rule model for continuous recon automation.
Stores recurring scan schedules with frequency and scope validation.
"""
from enum import Enum
from uuid import UUID

from sqlalchemy import ForeignKey, Index, String, Boolean, DateTime, Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime

from backend.database.base import BaseModel


class MonitoringFrequency(str, Enum):
    """Supported monitoring frequencies."""

    HOURLY = "hourly"
    DAILY = "daily"
    WEEKLY = "weekly"


class MonitoringRule(BaseModel):
    """
    Monitoring rule defining recurring automated reconnaissance.
    
    Rules schedule automatic scans at specified intervals with proper
    scope enforcement and frequency limiting to prevent queue overload.
    """

    __tablename__ = "monitoring_rules"

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
    
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    
    description: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    
    frequency: Mapped[str] = mapped_column(
        SQLEnum(MonitoringFrequency, name="monitoring_frequency_enum"),
        nullable=False,
        default=MonitoringFrequency.DAILY,
        server_default=MonitoringFrequency.DAILY.value,
        index=True,
    )
    
    enabled: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        index=True,
    )
    
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        index=True,
    )
    
    # Tracking
    last_run_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    
    last_run_status: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )
    
    created_by_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Relationships
    organization = relationship("Organization", foreign_keys=[organization_id])
    program = relationship("Program", foreign_keys=[program_id])
    created_by = relationship("User", foreign_keys=[created_by_id])

    __table_args__ = (
        Index("ix_monitoring_enabled", "enabled"),
        Index("ix_monitoring_org_prog", "organization_id", "program_id"),
        Index("ix_monitoring_freq", "frequency"),
    )
