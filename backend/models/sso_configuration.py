"""
SSO configuration model.
"""
from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import Boolean, ForeignKey, JSON, String, Index
from sqlalchemy.orm import Mapped, mapped_column

from backend.database.base import BaseModel


class SSOConfiguration(BaseModel):
    __tablename__ = "sso_configurations"

    organization_id: Mapped[UUID] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    provider_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    provider_metadata: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, index=True)

    __table_args__ = (
        Index("ix_sso_config_org_provider", "organization_id", "provider_type"),
    )
