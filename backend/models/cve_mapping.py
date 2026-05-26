"""
CVE correlation ORM model.
"""
from __future__ import annotations

from uuid import UUID

from sqlalchemy import ForeignKey, Index, String, Float
from sqlalchemy.orm import Mapped, mapped_column

from backend.database.base import BaseModel


class CVEMapping(BaseModel):
    __tablename__ = "cve_mappings"

    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    asset: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    cve_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    cvss_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    exploitability: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)

    __table_args__ = (
        Index("ix_cve_mapping_org_asset", "organization_id", "asset"),
        Index("ix_cve_mapping_org_cve", "organization_id", "cve_id"),
    )