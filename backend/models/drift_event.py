"""
Organization-scoped drift event model.
"""
from __future__ import annotations

from uuid import UUID

from sqlalchemy import ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database.base import BaseModel


class DriftEvent(BaseModel):
    """Infrastructure or authentication drift event."""

    __tablename__ = "drift_events"

    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    asset: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    drift_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    severity: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    summary: Mapped[str] = mapped_column(Text, nullable=False)

    organization = relationship("Organization", foreign_keys=[organization_id])

    __table_args__ = (
        Index("ix_drift_events_org_asset_created", "organization_id", "asset", "created_at"),
        Index("ix_drift_events_org_type_created", "organization_id", "drift_type", "created_at"),
    )

