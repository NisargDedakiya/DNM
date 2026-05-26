"""
API key ORM model for developer ecosystem access.
"""
from __future__ import annotations

from uuid import UUID

from sqlalchemy import ForeignKey, Index, JSON, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database.base import BaseModel


class ApiKey(BaseModel):
    __tablename__ = "api_keys"

    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    key_hash: Mapped[str] = mapped_column(String(128), nullable=False, unique=True, index=True)
    permissions: Mapped[list | None] = mapped_column(JSON, nullable=True)
    rate_limit: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    organization = relationship("Organization", foreign_keys=[organization_id])
    applications = relationship("DeveloperApplication", back_populates="api_key", passive_deletes=True)

    __table_args__ = (
        Index("ix_api_keys_org_created", "organization_id", "created_at"),
    )
