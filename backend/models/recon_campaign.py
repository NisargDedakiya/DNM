"""
Recon campaign ORM model for orchestrated campaign intelligence.
"""
from __future__ import annotations

from uuid import UUID

from sqlalchemy import ForeignKey, Index, JSON, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database.base import BaseModel


class ReconCampaign(BaseModel):
    __tablename__ = "recon_campaigns"

    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    campaign_name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(64), nullable=False, default="pending_approval", index=True)
    methodology: Mapped[dict | list | None] = mapped_column(JSON, nullable=True)

    organization = relationship("Organization", foreign_keys=[organization_id])

    __table_args__ = (
        Index("ix_recon_campaigns_org_created", "organization_id", "created_at"),
        Index("ix_recon_campaigns_org_status", "organization_id", "status"),
    )
