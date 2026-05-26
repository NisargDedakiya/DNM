"""
External exposure ORM model.
"""
from __future__ import annotations

from uuid import UUID

from sqlalchemy import ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from backend.database.base import BaseModel


class ExternalExposure(BaseModel):
    __tablename__ = "external_exposures"

    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    asset: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    source: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    exposure_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    severity: Mapped[str] = mapped_column(String(32), nullable=False, index=True)

    __table_args__ = (
        Index("ix_external_exposure_org_asset", "organization_id", "asset"),
        Index("ix_external_exposure_org_source", "organization_id", "source"),
    )