"""
Immutable audit log model.
"""
from __future__ import annotations

from uuid import UUID

from sqlalchemy import ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from backend.database.base import BaseModel


class AuditLog(BaseModel):
    __tablename__ = "audit_logs"

    organization_id: Mapped[UUID] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    actor: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    action: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    integrity_hash: Mapped[str] = mapped_column(String(128), nullable=False, index=True)

    __table_args__ = (
        Index("ix_audit_logs_org_actor", "organization_id", "actor"),
    )