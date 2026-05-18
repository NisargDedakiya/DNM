"""
ReportDraft model for historical AI-assisted report drafts.
"""
from __future__ import annotations

from uuid import UUID

from sqlalchemy import DateTime, Float, ForeignKey, Index, String, Text, func
from sqlalchemy import Uuid as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database.base import Base, UUIDMixin


class ReportDraft(Base, UUIDMixin):
    """Immutable report draft snapshots for auditability and review workflows."""

    __tablename__ = "report_drafts"

    finding_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("findings.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    platform: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    severity: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    report_content: Mapped[str] = mapped_column(Text, nullable=False)
    quality_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0, server_default="0")

    created_at: Mapped[object] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
    )

    finding = relationship("Finding", foreign_keys=[finding_id], lazy="select")

    __table_args__ = (
        Index("ix_report_drafts_finding_platform", "finding_id", "platform"),
        Index("ix_report_drafts_created_at", "created_at"),
    )
