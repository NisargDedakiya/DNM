"""
Blast radius ORM model.
"""
from __future__ import annotations

from uuid import UUID

from sqlalchemy import ForeignKey, Index, String, Float, JSON
from sqlalchemy.orm import Mapped, mapped_column

from backend.database.base import BaseModel


class BlastRadiusEvent(BaseModel):
    __tablename__ = "blast_radius_events"

    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    affected_assets: Mapped[list | None] = mapped_column(JSON, nullable=True)
    impact_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    summary: Mapped[str] = mapped_column(String(512), nullable=False)

    __table_args__ = (
        Index("ix_blast_radius_org", "organization_id"),
    )