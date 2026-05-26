"""
Privilege chain ORM model.
"""
from __future__ import annotations

from uuid import UUID

from sqlalchemy import ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from backend.database.base import BaseModel


class PrivilegeChain(BaseModel):
    __tablename__ = "privilege_chains"

    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    source_identity: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    escalated_privilege: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    severity: Mapped[str] = mapped_column(String(32), nullable=False, index=True)

    __table_args__ = (
        Index("ix_privilege_chain_org_source", "organization_id", "source_identity"),
    )