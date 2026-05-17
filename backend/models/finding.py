"""
Finding model for storing vulnerability findings.
"""
from enum import Enum
from uuid import UUID

from sqlalchemy import Enum as SQLEnum, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database.base import BaseModel


class SeverityLevel(str, Enum):
    """Finding severity levels."""

    info = "info"
    low = "low"
    medium = "medium"
    high = "high"
    critical = "critical"


class FindingStatus(str, Enum):
    """Workflow states for findings."""

    open = "open"
    triaged = "triaged"
    confirmed = "confirmed"
    fixed = "fixed"
    accepted = "accepted"
    duplicate = "duplicate"


class Finding(BaseModel):
    """Security finding linked to a program and optionally a scan."""

    __tablename__ = "findings"

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
    scan_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("scans.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    created_by_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    severity: Mapped[SeverityLevel] = mapped_column(
        SQLEnum(SeverityLevel, name="severity_level_enum", native_enum=True),
        nullable=False,
        index=True,
    )
    description: Mapped[str] = mapped_column(Text, nullable=False)
    endpoint: Mapped[str | None] = mapped_column(String(2048), nullable=True, index=True)
    evidence: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[FindingStatus] = mapped_column(
        SQLEnum(FindingStatus, name="finding_status_enum", native_enum=True),
        nullable=False,
        default=FindingStatus.open,
        server_default=FindingStatus.open.value,
        index=True,
    )

    program = relationship("Program", back_populates="findings")
    organization = relationship("Organization", back_populates="findings")
    scan = relationship("Scan", back_populates="findings")
    created_by = relationship("User", back_populates="findings")
    reports = relationship(
        "Report",
        back_populates="finding",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    
    __table_args__ = (
        Index("ix_findings_organization", "organization_id"),
    )

    __table_args__ = (
        Index("ix_findings_severity_status", "severity", "status"),
    )