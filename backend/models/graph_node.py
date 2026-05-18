"""
GraphNode model: a typed vertex in the security intelligence graph.

Each entity in the attack surface (asset, endpoint, technology, exposure,
finding, scan) is represented as a GraphNode.  Edges between nodes are stored
separately in GraphEdge.

Design principles
-----------------
- TYPED: ``node_type`` enforces a strict taxonomy of vertex kinds.
- REFERENCED: ``reference_id`` links back to the authoritative source row
  (e.g. assets.id) without coupling the graph schema to every domain table.
- WORKSPACE ISOLATED: every node carries ``organization_id``; all queries
  MUST filter on it.
- DEDUPLICATED: a unique constraint on (organization_id, node_type,
  reference_id) prevents duplicate nodes for the same entity.
- METADATA-RICH: ``node_metadata`` stores auxiliary signal (risk_score,
  hostname, severity …) so graph queries don't need cross-table joins for
  common attributes.
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
    UniqueConstraint,
    Enum as SQLEnum,
    func,
)
from sqlalchemy import Uuid as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database.base import Base, UUIDMixin


class NodeType(str, Enum):
    """Strict taxonomy of vertex kinds in the security graph."""

    ASSET = "asset"               # Discovered host / IP
    ENDPOINT = "endpoint"         # URL path on an asset
    TECHNOLOGY = "technology"     # Detected tech / framework
    EXPOSURE = "exposure"         # Active exposure finding
    FINDING = "finding"           # Structured vulnerability finding
    SCAN = "scan"                 # Recon scan run


class GraphNode(Base, UUIDMixin):
    """
    A vertex in the security intelligence graph.

    Columns
    -------
    organization_id : UUID
        Workspace isolation boundary.  All queries MUST include this filter.
    node_type : NodeType
        Entity category.
    reference_id : UUID
        Foreign key to the authoritative source row (assets.id, findings.id …).
        Stored as a plain UUID (no DB-level FK) so the graph layer stays
        decoupled from every domain table's lifecycle.
    label : str | None
        Human-readable label (hostname, path, CVE, …) for graph display.
    node_metadata : dict | None
        Lightweight attribute snapshot: risk_score, severity, version, etc.
        Avoids cross-table joins in hot graph-traversal paths.
    created_at : datetime
        Server-set insertion timestamp (immutable).
    """

    __tablename__ = "graph_nodes"

    # ── Workspace isolation ────────────────────────────────────────────────
    organization_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # ── Node identity ──────────────────────────────────────────────────────
    node_type: Mapped[str] = mapped_column(
        SQLEnum(NodeType),
        nullable=False,
        index=True,
    )

    reference_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        nullable=False,
        index=True,
        comment="UUID of the source row (asset, exposure, finding, …).",
    )

    # ── Display / attribute payload ────────────────────────────────────────
    label: Mapped[str | None] = mapped_column(
        String(512),
        nullable=True,
    )  # hostname, path, CVE id, technology name …

    node_metadata: Mapped[dict | None] = mapped_column(
        JSON,
        nullable=True,
    )  # {"risk_score": 7.5, "severity": "high", "is_alive": True, …}

    # ── Immutable creation timestamp ───────────────────────────────────────
    created_at: Mapped[object] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
    )

    # ── Outgoing / incoming edge navigation ───────────────────────────────
    outgoing_edges: Mapped[list["GraphEdge"]] = relationship(  # noqa: F821
        "GraphEdge",
        foreign_keys="GraphEdge.source_node_id",
        back_populates="source_node",
        cascade="all, delete-orphan",
        passive_deletes=True,
        lazy="select",
    )
    incoming_edges: Mapped[list["GraphEdge"]] = relationship(  # noqa: F821
        "GraphEdge",
        foreign_keys="GraphEdge.target_node_id",
        back_populates="target_node",
        cascade="all, delete-orphan",
        passive_deletes=True,
        lazy="select",
    )

    # ── Constraints & indexes ──────────────────────────────────────────────
    __table_args__ = (
        # Prevent duplicate nodes for the same source entity
        UniqueConstraint(
            "organization_id", "node_type", "reference_id",
            name="uq_graph_node_org_type_ref",
        ),
        Index("ix_graph_node_org_type", "organization_id", "node_type"),
        Index("ix_graph_node_org_ref", "organization_id", "reference_id"),
    )

    def __repr__(self) -> str:
        return (
            f"<GraphNode id={self.id} type={self.node_type} "
            f"label={self.label!r} org={self.organization_id}>"
        )
