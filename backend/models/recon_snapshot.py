"""
Recon Snapshot model: immutable point-in-time capture of the attack surface state.

Design principles:
- IMMUTABLE: snapshots are write-once; never updated after creation.
- SCALABLE: JSONB column stores full state; no row-per-asset explosion.
- AUDITABLE: every snapshot records who triggered it and why.
- ISOLATED: scoped to organization + program for strict workspace separation.
"""
from __future__ import annotations

from enum import Enum
from uuid import UUID

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Index,
    JSON,
    String,
    Text,
    Enum as SQLEnum,
    func,
)
from sqlalchemy import Uuid as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from backend.database.base import Base, UUIDMixin


class SnapshotType(str, Enum):
    """Snapshot domain categories captured during a recon run."""

    ASSETS = "assets"               # Discovered host inventory
    ENDPOINTS = "endpoints"         # Crawled/probed URL paths
    TECHNOLOGIES = "technologies"   # Detected tech stack
    EXPOSURES = "exposures"         # Active exposure findings
    FINDINGS = "findings"           # Structured vulnerability findings


class ReconSnapshot(Base, UUIDMixin):
    """
    Immutable point-in-time snapshot of a single domain of the attack surface.

    Once a row is inserted it must never be updated or deleted – the historical
    timeline integrity depends entirely on append-only storage.

    Columns
    -------
    organization_id : UUID
        Workspace isolation boundary; all queries MUST filter on this.
    program_id : UUID | None
        Optional program scope; NULL means an org-wide sweep.
    snapshot_type : SnapshotType
        Domain this snapshot covers (assets, endpoints, …).
    snapshot_data : dict
        Full serialised state at capture time.  Structure per type:
          assets      → [{"hostname", "ip_address", "is_alive", "risk_score", ...}]
          endpoints   → [{"path", "method", "status_code", "asset_id", ...}]
          technologies → [{"name", "version", "confidence_score", "asset_id", ...}]
          exposures   → [{"exposure_type", "risk_level", "asset_id", "title", ...}]
          findings    → [{"severity", "title", "cvss_score", "asset_id", ...}]
    trigger_source : str
        What initiated this snapshot: "monitoring_scan", "manual", "scheduled", "delta".
    triggered_by_scan_id : UUID | None
        If initiated by a scan run, the scan UUID for traceability.
    notes : str | None
        Human-readable context (e.g. "weekly scheduled sweep").
    created_at : datetime
        Server-side immutable timestamp; set once at insert.
    """

    __tablename__ = "recon_snapshots"

    # ── Workspace isolation ────────────────────────────────────────────────
    organization_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    program_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("programs.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )

    # ── Snapshot identity ─────────────────────────────────────────────────
    snapshot_type: Mapped[str] = mapped_column(
        SQLEnum(SnapshotType),
        nullable=False,
        index=True,
    )

    # ── Payload (immutable after insert) ──────────────────────────────────
    snapshot_data: Mapped[dict] = mapped_column(
        JSON,
        nullable=False,
    )

    # ── Provenance metadata ───────────────────────────────────────────────
    trigger_source: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        default="monitoring_scan",
    )  # "monitoring_scan" | "manual" | "scheduled" | "delta"

    triggered_by_scan_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("scans.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # ── Immutable timestamp ────────────────────────────────────────────────
    # Note: no updated_at – snapshots are append-only by design.
    created_at: Mapped[object] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
    )

    # ── Composite indexes for common query patterns ───────────────────────
    __table_args__ = (
        Index("ix_recon_snap_org_type_time", "organization_id", "snapshot_type", "created_at"),
        Index("ix_recon_snap_org_prog_type", "organization_id", "program_id", "snapshot_type"),
        Index("ix_recon_snap_scan", "triggered_by_scan_id"),
    )

    def __repr__(self) -> str:
        return (
            f"<ReconSnapshot id={self.id} type={self.snapshot_type} "
            f"org={self.organization_id} created={self.created_at}>"
        )
