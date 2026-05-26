"""
AnomalyEvent model tracking security posture anomalies.
"""
from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import ForeignKey, String, Text, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database.base import Base, UUIDMixin


class AnomalyEvent(Base, UUIDMixin):
    """
    Tracks anomalous mutations and risk spikes on the attack surface.
    """

    __tablename__ = "anomaly_events"

    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    anomaly_type: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
        index=True,
    )  # "risk_spike", "exposure_anomaly", "suspicious_mutation"
    severity: Mapped[str] = mapped_column(
        String(64),
        default="medium",
        nullable=False,
        index=True,
    )  # "critical", "high", "medium", "low"
    summary: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    detected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        nullable=False,
        index=True,
    )

    organization = relationship("Organization")

    def __repr__(self) -> str:
        return f"<AnomalyEvent id={self.id} type={self.anomaly_type} severity={self.severity}>"
