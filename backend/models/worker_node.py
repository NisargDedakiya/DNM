"""
Cluster worker node model.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, Float, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from backend.database.base import BaseModel


class WorkerNode(BaseModel):
    """Registered worker node in the distributed cluster."""

    __tablename__ = "worker_nodes"

    region: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="idle", index=True)
    current_load: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    health_score: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    last_heartbeat: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    organization_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    capabilities: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    metadata_: Mapped[dict[str, Any] | None] = mapped_column("metadata", JSON, nullable=True)

