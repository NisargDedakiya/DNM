"""
Developer application ORM model for ecosystem integrations.
"""
from __future__ import annotations

from uuid import UUID

from sqlalchemy import ForeignKey, Index, JSON, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database.base import BaseModel


class DeveloperApplication(BaseModel):
    __tablename__ = "developer_applications"

    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    api_key_id: Mapped[UUID] = mapped_column(
        ForeignKey("api_keys.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    usage_stats: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    organization = relationship("Organization", foreign_keys=[organization_id])
    api_key = relationship("ApiKey", back_populates="applications", foreign_keys=[api_key_id])

    __table_args__ = (
        Index("ix_developer_apps_org_created", "organization_id", "created_at"),
        Index("ix_developer_apps_org_name", "organization_id", "name"),
    )
