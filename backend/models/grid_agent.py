"""
GridAgent model tracking continuous monitoring grid agents.
"""
from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import ForeignKey, String, DateTime, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database.base import Base, UUIDMixin, TimestampMixin


class GridAgent(Base, UUIDMixin, TimestampMixin):
    """
    Represents an active, distributed continuous monitoring agent.
    """

    __tablename__ = "grid_agents"

    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    status: Mapped[str] = mapped_column(
        String(64),
        default="idle",
        nullable=False,
        index=True,
    )  # "idle", "active", "offline"
    monitored_assets: Mapped[dict] = mapped_column(
        JSON,
        default=dict,
        nullable=False,
    )  # JSON dictionary of assets being monitored, e.g. {"asset_ids": [...]}
    last_heartbeat: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        nullable=False,
    )

    organization = relationship("Organization")

    def __repr__(self) -> str:
        return f"<GridAgent id={self.id} org={self.organization_id} status={self.status}>"
