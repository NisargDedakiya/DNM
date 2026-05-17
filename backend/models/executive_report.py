"""
ExecutiveReport model: organisation-scoped executive intelligence reports.

Distinct from the existing ``Report`` model (which is finding-scoped and AI
content), this model stores full executive intelligence snapshots generated
by the reporting engine — exposure summaries, attack surface reports,
executive briefs, and risk trend documents.

Design principles
-----------------
- HISTORICAL:   rows are never updated; each generation creates a new row.
- AUDITABLE:    ``generated_by`` records the user or system that triggered
                the report, and ``created_at`` is server-set and immutable.
- WORKSPACE ISOLATED: ``organization_id`` scopes every report to one tenant.
- STRUCTURED:   ``report_data`` stores the full structured payload (metrics,
                lists, trend data) so consumers don't have to re-compute it.
- EXPORTABLE:   ``content_markdown`` stores the pre-rendered markdown for
                safe, sanitised text export without re-rendering.
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
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database.base import Base, UUIDMixin


class ExecutiveReportType(str, Enum):
    """Categories of executive intelligence reports."""

    EXPOSURE_SUMMARY = "exposure_summary"           # Snapshot of active exposures
    ATTACK_SURFACE_REPORT = "attack_surface_report" # Full attack surface topology
    EXECUTIVE_BRIEF = "executive_brief"             # High-level C-suite summary
    RISK_TRENDS = "risk_trends"                     # Longitudinal risk evolution
    POSTURE_REPORT = "posture_report"               # Security posture scorecard


class ExecutiveReport(Base, UUIDMixin):
    """
    Immutable executive intelligence report row.

    Columns
    -------
    organization_id : UUID
        Workspace isolation — mandatory on all reports.
    report_type : ExecutiveReportType
        Category of intelligence being reported.
    title : str
        Human-readable report title (auto-generated or user-provided).
    summary : str | None
        One-paragraph executive summary (plain text, sanitised).
    report_data : dict | None
        Full structured payload: metrics, lists, trend arrays.
        Safe to serialise to JSON for API responses.
    content_markdown : str | None
        Pre-rendered Markdown content for text export.
        Sanitised by the reporting service before storage.
    generated_by : UUID | None
        User ID who triggered the report (NULL = system-generated).
    program_id : UUID | None
        Optional program scope for program-specific reports.
    created_at : datetime
        Server-set immutable creation timestamp.
    """

    __tablename__ = "executive_reports"

    # ── Workspace isolation ────────────────────────────────────────────────
    organization_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    program_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("programs.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # ── Report identity ───────────────────────────────────────────────────
    report_type: Mapped[str] = mapped_column(
        SQLEnum(ExecutiveReportType),
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(512), nullable=False)

    # ── Content ───────────────────────────────────────────────────────────
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    report_data: Mapped[dict | None] = mapped_column(
        JSON,
        nullable=True,
        comment="Structured payload: metrics, lists, trend data.",
    )
    content_markdown: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Pre-rendered, sanitised Markdown export content.",
    )

    # ── Provenance ─────────────────────────────────────────────────────────
    generated_by: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # ── Immutable creation timestamp ───────────────────────────────────────
    created_at: Mapped[object] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
    )

    # ── ORM navigation ─────────────────────────────────────────────────────
    organization = relationship(
        "Organization",
        foreign_keys=[organization_id],
        lazy="select",
    )
    generated_by_user = relationship(
        "User",
        foreign_keys=[generated_by],
        lazy="select",
    )

    # ── Indexes ────────────────────────────────────────────────────────────
    __table_args__ = (
        Index("ix_exec_report_org_type_time", "organization_id", "report_type", "created_at"),
        Index("ix_exec_report_org_time", "organization_id", "created_at"),
    )

    def __repr__(self) -> str:
        return (
            f"<ExecutiveReport id={self.id} type={self.report_type} "
            f"org={self.organization_id} created={self.created_at}>"
        )
