"""
ExposureMutation model tracking changes in the attack surface.
"""
from __future__ import annotations

from uuid import UUID

from sqlalchemy import ForeignKey, String, Text, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database.base import Base, UUIDMixin, TimestampMixin


class ExposureMutation(Base, UUIDMixin, TimestampMixin):
    """
    Tracks mutations and drift detected on monitored assets.
    """

    __tablename__ = "exposure_mutations"

    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    asset: Mapped[dict] = mapped_column(
        JSON,
        nullable=False,
    )  # JSON representation of the asset details, e.g. {"id": "...", "hostname": "...", "ip_address": "..."}
    mutation_type: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
        index=True,
    )  # "dns_drift", "cloud_exposure", "auth_mutation", "port_open"
    severity: Mapped[str] = mapped_column(
        String(64),
        default="info",
        nullable=False,
        index=True,
    )  # "critical", "high", "medium", "low", "info"
    summary: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    organization = relationship("Organization")

    def __repr__(self) -> str:
        return f"<ExposureMutation id={self.id} type={self.mutation_type} severity={self.severity}>"
