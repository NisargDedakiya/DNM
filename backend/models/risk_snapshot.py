"""
Historical risk snapshot model for organization-level risk evolution.
"""
from __future__ import annotations

from uuid import UUID

from sqlalchemy import ForeignKey, Index, Float, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database.base import BaseModel


class RiskSnapshot(BaseModel):
    """Point-in-time organization risk snapshot."""

    __tablename__ = "risk_snapshots"

    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    risk_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    summary: Mapped[str] = mapped_column(Text, nullable=False)

    organization = relationship("Organization", foreign_keys=[organization_id])

    __table_args__ = (
        Index("ix_risk_snapshots_org_created", "organization_id", "created_at"),
        Index("ix_risk_snapshots_org_score", "organization_id", "risk_score"),
    )

