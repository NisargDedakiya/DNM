"""
Hunt strategy ORM model for autonomous campaign planning.
"""
from __future__ import annotations

from uuid import UUID

from sqlalchemy import ForeignKey, Index, JSON, Float, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database.base import BaseModel


class HuntStrategy(BaseModel):
    __tablename__ = "hunt_strategies"

    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    strategy_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    target_scope: Mapped[dict | list | None] = mapped_column(JSON, nullable=True)
    priority_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)

    organization = relationship("Organization", foreign_keys=[organization_id])

    __table_args__ = (
        Index("ix_hunt_strategies_org_created", "organization_id", "created_at"),
        Index("ix_hunt_strategies_org_type", "organization_id", "strategy_type"),
    )

