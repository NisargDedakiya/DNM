"""
Federated identity mapping model.
"""
from __future__ import annotations

from uuid import UUID

from sqlalchemy import ForeignKey, String, Index
from sqlalchemy.orm import Mapped, mapped_column

from backend.database.base import BaseModel


class FederatedIdentity(BaseModel):
    __tablename__ = "federated_identities"

    organization_id: Mapped[UUID] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    external_identity: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    provider: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    mapped_user_id: Mapped[UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    __table_args__ = (
        Index("ix_federated_identity_org_provider", "organization_id", "provider"),
    )
