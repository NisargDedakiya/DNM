"""
Recovery snapshot model.
"""
from __future__ import annotations

from uuid import UUID

from sqlalchemy import ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from backend.database.base import BaseModel


class RecoverySnapshot(BaseModel):
    __tablename__ = "recovery_snapshots"

    organization_id: Mapped[UUID] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    snapshot_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    storage_location: Mapped[str] = mapped_column(String(255), nullable=False)

    __table_args__ = (
        Index("ix_recovery_snapshots_org_type", "organization_id", "snapshot_type"),
    )