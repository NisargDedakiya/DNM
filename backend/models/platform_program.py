"""
PlatformProgram model: normalised bug bounty program records imported from
external platforms (HackerOne, Bugcrowd, Intigriti, YesWeHack, etc.).

Design principles
-----------------
- MULTI-PLATFORM:   ``platform_name`` + ``external_program_id`` form the
                    natural key per organisation.
- NORMALISED:       ``scope_data`` (JSONB) stores the full normalised scope
                    payload so the recon engine can consume it directly
                    without knowing the source platform's schema.
- IDEMPOTENT SYNC:  ``synced_at`` tracks when the record was last refreshed;
                    upsert logic in PlatformSyncService keeps one row per
                    (org, platform, external_program_id) — no duplicates.
- WORKSPACE ISOLATED: ``organization_id`` is NOT NULL; FK-constrained.
- AUDITABLE:        ``created_at`` + ``synced_at`` give full sync history.

Scope data schema (normalised, platform-agnostic)
-------------------------------------------------
{
  "in_scope": [
    {
      "target": "*.example.com",
      "target_type": "url" | "cidr" | "mobile" | "other",
      "instruction": "...",
      "max_severity": "critical" | "high" | ...
    }
  ],
  "out_of_scope": [
    {"target": "staging.example.com", "target_type": "url", "instruction": ""}
  ],
  "raw_platform_data": {}     # original platform payload (truncated at 64 KB)
}
"""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from uuid import UUID

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Index,
    JSON,
    String,
    UniqueConstraint,
    Enum as SQLEnum,
    func,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database.base import Base, UUIDMixin


class PlatformName(str, Enum):
    """Supported bug bounty platforms."""
    HACKERONE = "hackerone"
    BUGCROWD = "bugcrowd"
    INTIGRITI = "intigriti"
    YESWEHACK = "yeswehack"
    MANUAL = "manual"           # user-created programs (no platform sync)


class ScopeTargetType(str, Enum):
    """Normalised scope target types across all platforms."""
    URL = "url"
    CIDR = "cidr"
    MOBILE_APP = "mobile"
    HARDWARE = "hardware"
    OTHER = "other"


class PlatformProgram(Base, UUIDMixin):
    """
    Normalised bug bounty program record imported from an external platform.

    Columns
    -------
    organization_id : UUID
        Workspace isolation — NOT NULL.
    platform_name : PlatformName
        Source platform enum.
    external_program_id : str
        Platform's own ID/handle for this program (e.g. HackerOne handle).
    program_name : str
        Human-readable program name.
    program_handle : str | None
        Platform slug / handle (e.g. ``uber`` on HackerOne).
    program_url : str | None
        Direct URL to the program's bug bounty page.
    is_private : bool
        Whether the program is invite-only.
    offers_bounty : bool
        Whether the program pays monetary rewards.
    scope_data : dict
        Normalised scope payload (see module docstring for schema).
    sync_status : str
        "ok" | "error" | "pending" — last sync result.
    sync_error : str | None
        Human-readable sync error if sync_status == "error".
    synced_at : datetime | None
        Timestamp of most recent successful sync.
    created_at : datetime
        Row creation timestamp (server-set, immutable).
    """

    __tablename__ = "platform_programs"

    # ── Workspace isolation ─────────────────────────────────────────────────
    organization_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # ── Platform identity ───────────────────────────────────────────────────
    platform_name: Mapped[str] = mapped_column(
        SQLEnum(PlatformName),
        nullable=False,
        index=True,
    )
    external_program_id: Mapped[str] = mapped_column(
        String(512),
        nullable=False,
        index=True,
    )
    program_name: Mapped[str] = mapped_column(String(512), nullable=False)
    program_handle: Mapped[str | None] = mapped_column(String(255), nullable=True)
    program_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)

    # ── Program metadata ────────────────────────────────────────────────────
    is_private: Mapped[bool] = mapped_column(
        nullable=False, default=False, server_default="false"
    )
    offers_bounty: Mapped[bool] = mapped_column(
        nullable=False, default=True, server_default="true"
    )

    # ── Normalised scope payload ─────────────────────────────────────────────
    scope_data: Mapped[dict | None] = mapped_column(
        JSON,
        nullable=True,
        comment="Normalised scope: {in_scope:[], out_of_scope:[], raw_platform_data:{}}",
    )

    # ── Sync provenance ──────────────────────────────────────────────────────
    sync_status: Mapped[str] = mapped_column(
        String(16), nullable=False, default="pending", server_default="pending"
    )
    sync_error: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    synced_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # ── Immutable creation timestamp ─────────────────────────────────────────
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # ── ORM navigation ───────────────────────────────────────────────────────
    organization = relationship(
        "Organization",
        foreign_keys=[organization_id],
        lazy="select",
    )

    # ── Constraints & indexes ────────────────────────────────────────────────
    __table_args__ = (
        UniqueConstraint(
            "organization_id", "platform_name", "external_program_id",
            name="uq_platform_program_org_platform_extid",
        ),
        Index("ix_platform_program_org_platform", "organization_id", "platform_name"),
        Index("ix_platform_program_synced_at", "synced_at"),
    )

    def __repr__(self) -> str:
        return (
            f"<PlatformProgram platform={self.platform_name} "
            f"handle={self.program_handle} org={self.organization_id}>"
        )
