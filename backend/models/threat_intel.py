"""
Threat intelligence ORM model.
"""
from __future__ import annotations

from uuid import UUID

from sqlalchemy import ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from backend.database.base import BaseModel


class ThreatIntel(BaseModel):
    __tablename__ = "threat_intel"

    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    asset: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    intelligence_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    severity: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    summary: Mapped[str] = mapped_column(Text, nullable=False)

    __table_args__ = (
        Index("ix_threat_intel_org_asset", "organization_id", "asset"),
        Index("ix_threat_intel_org_type", "organization_id", "intelligence_type"),
    )