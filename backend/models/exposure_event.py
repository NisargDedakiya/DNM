"""
Exposure history event model for asset drift and authentication change tracking.
"""
from __future__ import annotations

from uuid import UUID

from sqlalchemy import ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database.base import BaseModel


class ExposureEvent(BaseModel):
    """Historical exposure event scoped to a single organization."""

    __tablename__ = "exposure_events"

    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    asset: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    severity: Mapped[str] = mapped_column(String(32), nullable=False, index=True)

    organization = relationship("Organization", foreign_keys=[organization_id])

    __table_args__ = (
        Index("ix_exposure_events_org_asset_created", "organization_id", "asset", "created_at"),
        Index("ix_exposure_events_org_event_created", "organization_id", "event_type", "created_at"),
    )

