"""
Private workspace model.
"""
from __future__ import annotations

from uuid import UUID

from sqlalchemy import Boolean, ForeignKey, String, Index
from sqlalchemy.orm import Mapped, mapped_column

from backend.database.base import BaseModel


class PrivateWorkspace(BaseModel):
    __tablename__ = "private_workspaces"

    organization_id: Mapped[UUID] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    stealth_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, index=True)
    created_by: Mapped[UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    __table_args__ = (
        Index("ix_private_workspace_org_name", "organization_id", "name"),
    )
