"""
HackerOneReport model: historical report tracking for organization workspaces.
"""
from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Index, String, UniqueConstraint, func
from sqlalchemy import Uuid as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database.base import Base, UUIDMixin


class HackerOneReport(Base, UUIDMixin):
    """Organization-scoped HackerOne report metadata cache."""

    __tablename__ = "hackerone_reports"

    organization_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    hackerone_report_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(1024), nullable=False)
    severity: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    state: Mapped[str] = mapped_column(String(64), nullable=False, index=True)

    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
    )

    organization = relationship("Organization", foreign_keys=[organization_id], lazy="select")

    __table_args__ = (
        UniqueConstraint(
            "organization_id",
            "hackerone_report_id",
            name="uq_h1_report_org_external_id",
        ),
        Index("ix_h1_report_org_state", "organization_id", "state"),
    )
