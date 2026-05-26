"""
Persistent hunt memory model for organization-isolated AI intelligence.
"""
from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import Index, JSON, String, Text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database.base import BaseModel


class HuntMemory(BaseModel):
    """Historical hunt memory scoped to a single organization."""

    __tablename__ = "hunt_memory"

    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    memory_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    metadata_: Mapped[dict[str, Any] | None] = mapped_column("metadata", JSON, nullable=True)

    organization = relationship("Organization", foreign_keys=[organization_id])

    __table_args__ = (
        Index("ix_hunt_memory_org_type_created", "organization_id", "memory_type", "created_at"),
    )

