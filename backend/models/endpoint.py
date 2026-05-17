"""
Endpoint model: tracks discovered paths for assets.
"""
from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import ForeignKey, Index, String, Integer, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database.base import BaseModel


class Endpoint(BaseModel):
    __tablename__ = "endpoints"

    asset_id: Mapped[UUID] = mapped_column(ForeignKey("assets.id", ondelete="CASCADE"), nullable=False, index=True)
    path: Mapped[str] = mapped_column(String(2048), nullable=False, index=True)
    method: Mapped[str] = mapped_column(String(10), nullable=False, default="GET")
    status_code: Mapped[int | None] = mapped_column(Integer, nullable=True)
    content_type: Mapped[str | None] = mapped_column(String(255), nullable=True)
    first_seen: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_seen: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    asset = relationship("Asset", back_populates="endpoints")

    __table_args__ = (
        Index("ix_endpoints_asset_path", "asset_id", "path"),
    )
