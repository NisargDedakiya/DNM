"""
Organization-scoped exposure snapshot model.
"""
from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import ForeignKey, Index, Float, JSON, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database.base import BaseModel


class ExposureSnapshot(BaseModel):
    """Snapshot of an asset or organization exposure state."""

    __tablename__ = "exposure_snapshots"

    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    asset: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    exposure_state: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    risk_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)

    organization = relationship("Organization", foreign_keys=[organization_id])

    __table_args__ = (
        Index("ix_exposure_snapshots_org_asset_created", "organization_id", "asset", "created_at"),
        Index("ix_exposure_snapshots_org_score", "organization_id", "risk_score"),
    )

