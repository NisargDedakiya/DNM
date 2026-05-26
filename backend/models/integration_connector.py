"""
Integration connector ORM model for marketplace-managed integrations.
"""
from __future__ import annotations

from uuid import UUID

from sqlalchemy import Boolean, ForeignKey, Index, JSON, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database.base import BaseModel


class IntegrationConnector(BaseModel):
    __tablename__ = "integration_connectors"

    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    connector_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    configuration: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, index=True)

    organization = relationship("Organization", foreign_keys=[organization_id])

    __table_args__ = (
        Index("ix_connector_org_type", "organization_id", "connector_type"),
        Index("ix_connector_org_enabled", "organization_id", "enabled"),
    )
