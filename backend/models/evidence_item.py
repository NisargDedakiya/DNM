"""
Evidence artifact model for collaborative investigations.
"""
from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import ForeignKey, Index, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database.base import BaseModel


class EvidenceItem(BaseModel):
    """Versioned evidence artifact linked to an investigation."""

    __tablename__ = "evidence_items"

    investigation_id: Mapped[UUID] = mapped_column(ForeignKey("investigations.id", ondelete="CASCADE"), nullable=False, index=True)
    file_path: Mapped[str] = mapped_column(String(2048), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    uploaded_by: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    evidence_type: Mapped[str] = mapped_column(String(32), nullable=False, default="note", index=True)
    checksum: Mapped[str | None] = mapped_column(String(128), nullable=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    parent_evidence_id: Mapped[UUID | None] = mapped_column(ForeignKey("evidence_items.id", ondelete="SET NULL"), nullable=True, index=True)
    metadata_: Mapped[dict[str, Any] | None] = mapped_column("metadata", JSON, nullable=True)

    investigation = relationship("Investigation", back_populates="evidence_items")
    uploader = relationship("User")
    parent_evidence = relationship("EvidenceItem", remote_side="EvidenceItem.id")

    __table_args__ = (
        Index("ix_evidence_items_investigation_version", "investigation_id", "version"),
    )
