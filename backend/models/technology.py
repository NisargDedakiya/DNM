"""
Technology model: detected technologies per asset.
"""
from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import ForeignKey, Index, String, Float, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database.base import BaseModel


class Technology(BaseModel):
    __tablename__ = "technologies"

    asset_id: Mapped[UUID] = mapped_column(ForeignKey("assets.id", ondelete="CASCADE"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    version: Mapped[str | None] = mapped_column(String(100), nullable=True)
    confidence_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    first_detected: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    asset = relationship("Asset", back_populates="technologies")

    __table_args__ = (
        Index("ix_technologies_asset_name", "asset_id", "name"),
    )
