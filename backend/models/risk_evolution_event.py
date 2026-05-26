"""
Organization-scoped risk evolution event model.
"""
from __future__ import annotations

from uuid import UUID

from sqlalchemy import ForeignKey, Index, Float, Text, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database.base import BaseModel


class RiskEvolutionEvent(BaseModel):
    """Historical risk delta event for a single asset."""

    __tablename__ = "risk_evolution_events"

    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    asset: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    previous_risk: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    current_risk: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    summary: Mapped[str] = mapped_column(Text, nullable=False)

    organization = relationship("Organization", foreign_keys=[organization_id])

    __table_args__ = (
        Index("ix_risk_evolution_org_asset_created", "organization_id", "asset", "created_at"),
        Index("ix_risk_evolution_org_risk_created", "organization_id", "current_risk", "created_at"),
    )

