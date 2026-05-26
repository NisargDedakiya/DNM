"""
Collaborative investigation model.
"""
from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database.base import BaseModel


class Investigation(BaseModel):
    """Org-scoped collaborative investigation workspace."""

    __tablename__ = "investigations"

    organization_id: Mapped[str] = mapped_column(String(64), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    severity: Mapped[str] = mapped_column(String(32), nullable=False, default="medium", index=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="open", index=True)
    assigned_to: Mapped[UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    source_finding_id: Mapped[UUID | None] = mapped_column(ForeignKey("findings.id", ondelete="SET NULL"), nullable=True, index=True)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    workflow_stage: Mapped[str] = mapped_column(String(32), nullable=False, default="open", index=True)

    comments = relationship("InvestigationComment", back_populates="investigation", cascade="all, delete-orphan", passive_deletes=True)
    evidence_items = relationship("EvidenceItem", back_populates="investigation", cascade="all, delete-orphan", passive_deletes=True)
    assignments = relationship("TaskAssignment", back_populates="investigation", cascade="all, delete-orphan", passive_deletes=True)

    __table_args__ = (
        Index("ix_investigations_org_status", "organization_id", "status"),
        Index("ix_investigations_org_severity", "organization_id", "severity"),
    )
