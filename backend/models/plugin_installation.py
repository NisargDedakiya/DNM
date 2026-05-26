"""
Plugin installation ORM model for org-scoped deployments.
"""
from __future__ import annotations

from uuid import UUID

from sqlalchemy import ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database.base import BaseModel


class PluginInstallation(BaseModel):
    __tablename__ = "plugin_installations"

    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    plugin_id: Mapped[UUID] = mapped_column(
        ForeignKey("plugins.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    installed_by: Mapped[UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    installed_at: Mapped[str | None] = mapped_column(String(64), nullable=True)

    organization = relationship("Organization", foreign_keys=[organization_id])
    plugin = relationship("Plugin", back_populates="installations", foreign_keys=[plugin_id])
    installed_by_user = relationship("User", foreign_keys=[installed_by])

    __table_args__ = (
        Index("ix_plugin_installations_org_created", "organization_id", "created_at"),
        Index("ix_plugin_installations_org_plugin", "organization_id", "plugin_id"),
    )
