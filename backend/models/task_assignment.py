"""
Task assignment model for investigation ownership and escalation.
"""
from __future__ import annotations

from uuid import UUID

from sqlalchemy import ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database.base import BaseModel


class TaskAssignment(BaseModel):
    """Tracks investigation ownership and assignment status."""

    __tablename__ = "task_assignments"

    investigation_id: Mapped[UUID] = mapped_column(ForeignKey("investigations.id", ondelete="CASCADE"), nullable=False, index=True)
    assignee_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="assigned", index=True)
    assigned_at: Mapped[str] = mapped_column(String(64), nullable=False)
    assigned_by: Mapped[UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    escalation_level: Mapped[str | None] = mapped_column(String(32), nullable=True)
    escalation_reason: Mapped[str | None] = mapped_column(String(255), nullable=True)

    investigation = relationship("Investigation", back_populates="assignments")
    assignee = relationship("User", foreign_keys=[assignee_id])
    assigner = relationship("User", foreign_keys=[assigned_by])

    __table_args__ = (
        Index("ix_task_assignments_investigation_status", "investigation_id", "status"),
    )
