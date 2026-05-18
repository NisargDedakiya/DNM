"""
TriageResult model: immutable AI triage snapshots for findings.
"""
from __future__ import annotations

from uuid import UUID

from sqlalchemy import DateTime, Float, ForeignKey, Index, String, Text, func
from sqlalchemy import Uuid as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database.base import Base, UUIDMixin


class TriageResult(Base, UUIDMixin):
    """Historical triage output for audit-safe finding prioritization."""

    __tablename__ = "triage_results"

    organization_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    finding_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("findings.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    severity: Mapped[str] = mapped_column(String(8), nullable=False, index=True)
    confidence_score: Mapped[float] = mapped_column(Float, nullable=False)
    exploitability_score: Mapped[float] = mapped_column(Float, nullable=False)

    ai_summary: Mapped[str] = mapped_column(Text, nullable=False)
    reasoning: Mapped[str] = mapped_column(Text, nullable=False)

    created_at: Mapped[object] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
    )

    organization = relationship("Organization", foreign_keys=[organization_id], lazy="select")
    finding = relationship("Finding", foreign_keys=[finding_id], lazy="select")

    __table_args__ = (
        Index("ix_triage_results_org_finding", "organization_id", "finding_id"),
        Index("ix_triage_results_org_created", "organization_id", "created_at"),
    )
