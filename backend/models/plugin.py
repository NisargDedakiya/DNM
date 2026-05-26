"""
Plugin ORM model for marketplace-listed extensions.
"""
from __future__ import annotations

from uuid import UUID

from sqlalchemy import ForeignKey, Index, JSON, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database.base import BaseModel


class Plugin(BaseModel):
    __tablename__ = "plugins"

    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    version: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    permissions: Mapped[list | None] = mapped_column(JSON, nullable=True)

    organization = relationship("Organization", foreign_keys=[organization_id])
    installations = relationship("PluginInstallation", back_populates="plugin", passive_deletes=True)

    __table_args__ = (
        Index("ix_plugins_org_name", "organization_id", "name"),
        Index("ix_plugins_org_version", "organization_id", "version"),
    )
