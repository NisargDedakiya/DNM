"""
HackerOneProgram model: normalized storage for synchronized HackerOne programs.
"""
from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, String, UniqueConstraint, func
from sqlalchemy import Uuid as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database.base import Base, UUIDMixin


class HackerOneProgram(Base, UUIDMixin):
    """Organization-scoped HackerOne program snapshot."""

    __tablename__ = "hackerone_programs"

    organization_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    hackerone_program_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    handle: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(512), nullable=False)

    bounty_enabled: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
    )
    offers_bounties: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
    )

    synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
    )

    organization = relationship("Organization", foreign_keys=[organization_id], lazy="select")

    __table_args__ = (
        UniqueConstraint(
            "organization_id",
            "hackerone_program_id",
            name="uq_h1_program_org_external_id",
        ),
        Index("ix_h1_program_org_handle", "organization_id", "handle"),
    )
