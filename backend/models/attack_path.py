"""
Attack path ORM model.
"""
from __future__ import annotations

from uuid import UUID

from sqlalchemy import ForeignKey, Index, String, Float
from sqlalchemy.orm import Mapped, mapped_column

from backend.database.base import BaseModel


class AttackPath(BaseModel):
    __tablename__ = "attack_paths"

    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    source_asset: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    target_asset: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    severity: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    exploitability_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)

    __table_args__ = (
        Index("ix_attack_path_org_source", "organization_id", "source_asset"),
        Index("ix_attack_path_org_target", "organization_id", "target_asset"),
    )