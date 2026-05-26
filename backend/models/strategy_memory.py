"""
Strategy memory ORM model for learning from successful hunts.
"""
from __future__ import annotations

from uuid import UUID

from sqlalchemy import ForeignKey, Index, JSON, Float
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database.base import BaseModel


class StrategyMemory(BaseModel):
    __tablename__ = "strategy_memory"

    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    methodology_pattern: Mapped[dict | list | None] = mapped_column(JSON, nullable=True)
    success_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)

    organization = relationship("Organization", foreign_keys=[organization_id])

    __table_args__ = (
        Index("ix_strategy_memory_org_created", "organization_id", "created_at"),
        Index("ix_strategy_memory_org_success", "organization_id", "success_score"),
    )
