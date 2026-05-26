"""
Cluster job model for distributed scan execution.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Index, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database.base import BaseModel


class ClusterJob(BaseModel):
    """Queued cluster job with worker assignment and lifecycle tracking."""

    __tablename__ = "cluster_jobs"

    organization_id: Mapped[str] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    task_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    priority: Mapped[str] = mapped_column(String(16), nullable=False, default="medium", index=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="queued", index=True)
    assigned_worker: Mapped[UUID | None] = mapped_column(
        ForeignKey("worker_nodes.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    payload: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    failure_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    worker = relationship("WorkerNode", foreign_keys=[assigned_worker])

    __table_args__ = (
        Index("ix_cluster_jobs_org_status_priority", "organization_id", "status", "priority"),
        Index("ix_cluster_jobs_org_created", "organization_id", "created_at"),
    )

