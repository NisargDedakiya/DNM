"""
Scan model for async scan execution tracking.
"""
from datetime import datetime
from enum import Enum
from uuid import UUID

from sqlalchemy import DateTime, Enum as SQLEnum, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database.base import BaseModel


class ScanType(str, Enum):
    """Supported scan categories."""

    recon = "recon"
    surface = "surface"
    deep = "deep"
    manual = "manual"


class ScanStatus(str, Enum):
    """Lifecycle states for scan execution."""

    pending = "pending"
    running = "running"
    completed = "completed"
    failed = "failed"
    cancelled = "cancelled"


class Scan(BaseModel):
    """Background scan execution record."""

    __tablename__ = "scans"

    program_id: Mapped[UUID] = mapped_column(
        ForeignKey("programs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    organization_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    created_by_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    scan_type: Mapped[ScanType] = mapped_column(
        SQLEnum(ScanType, name="scan_type_enum", native_enum=True),
        nullable=False,
        index=True,
    )
    status: Mapped[ScanStatus] = mapped_column(
        SQLEnum(ScanStatus, name="scan_status_enum", native_enum=True),
        nullable=False,
        default=ScanStatus.pending,
        server_default=ScanStatus.pending.value,
        index=True,
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    program = relationship("Program", back_populates="scans")
    organization = relationship("Organization", back_populates="scans")
    created_by = relationship("User", back_populates="scans")
    findings = relationship(
        "Finding",
        back_populates="scan",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


