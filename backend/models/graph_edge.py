"""
GraphEdge model: a directed, typed edge in the security intelligence graph.

Edges connect two GraphNode vertices with a typed relationship and a
confidence score.  Together, nodes and edges form a queryable property graph
that represents the attack surface topology.

Relationship taxonomy
---------------------
- hosts         : asset → endpoint          (an asset hosts this endpoint)
- exposes       : asset → exposure          (an asset exposes this risk)
- depends_on    : asset/endpoint → technology (runtime dependency)
- related_to    : finding → finding / exposure → exposure (correlation)
- discovered_by : asset/finding → scan      (which scan found this)
- affected_by   : asset → finding           (this asset is affected by this finding)

Design principles
-----------------
- DIRECTED: source → target; direction carries semantic meaning.
- TYPED: ``relationship_type`` enforces the taxonomy above.
- CONFIDENCE-SCORED: 0.0–1.0 quality signal for risk propagation weighting.
- NO SELF-LOOPS: enforced at service layer, not DB (performance trade-off).
- WORKSPACE ISOLATED: ``organization_id`` on every edge row.
- DUPLICATE SAFE: unique constraint prevents parallel edges of the same type.
"""
from __future__ import annotations

from enum import Enum
from uuid import UUID

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
    Enum as SQLEnum,
    func,
)
from sqlalchemy import Uuid as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database.base import Base, UUIDMixin


class RelationshipType(str, Enum):
    """Typed taxonomy of directed edges in the security graph."""

    HOSTS = "hosts"                   # asset → endpoint
    EXPOSES = "exposes"               # asset → exposure
    DEPENDS_ON = "depends_on"         # asset/endpoint → technology
    RELATED_TO = "related_to"         # finding ↔ finding / exposure ↔ exposure
    DISCOVERED_BY = "discovered_by"   # entity → scan
    AFFECTED_BY = "affected_by"       # asset → finding


class GraphEdge(Base, UUIDMixin):
    """
    A directed, typed edge connecting two GraphNode vertices.

    Columns
    -------
    organization_id : UUID
        Workspace isolation — must match both source and target node orgs.
    source_node_id : UUID
        The originating node of the directed edge.
    target_node_id : UUID
        The destination node of the directed edge.
    relationship_type : RelationshipType
        Semantic meaning of the connection.
    confidence_score : float
        Quality / certainty of this relationship [0.0–1.0].  Used by
        risk-propagation algorithms to weight edge traversal.
    weight : float
        Traversal weight [0.0–1.0]; defaults to confidence_score but can be
        overridden by analytics services for specific algorithms.
    notes : str | None
        Optional human-readable context about why this edge exists.
    created_at : datetime
        Server-set immutable creation timestamp.
    """

    __tablename__ = "graph_edges"

    # ── Workspace isolation ────────────────────────────────────────────────
    organization_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # ── Directed edge endpoints ────────────────────────────────────────────
    source_node_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("graph_nodes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    target_node_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("graph_nodes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # ── Edge semantics ─────────────────────────────────────────────────────
    relationship_type: Mapped[str] = mapped_column(
        SQLEnum(RelationshipType),
        nullable=False,
        index=True,
    )

    confidence_score: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=1.0,
    )  # 0.0–1.0

    weight: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=1.0,
    )  # Traversal / propagation weight; can diverge from confidence_score

    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # ── Immutable creation timestamp ───────────────────────────────────────
    created_at: Mapped[object] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
    )

    # ── Relationships (ORM navigation) ─────────────────────────────────────
    source_node: Mapped["GraphNode"] = relationship(  # noqa: F821
        "GraphNode",
        foreign_keys=[source_node_id],
        back_populates="outgoing_edges",
        lazy="select",
    )
    target_node: Mapped["GraphNode"] = relationship(  # noqa: F821
        "GraphNode",
        foreign_keys=[target_node_id],
        back_populates="incoming_edges",
        lazy="select",
    )

    # ── Constraints & indexes ──────────────────────────────────────────────
    __table_args__ = (
        # Prevent duplicate directed edges of the same relationship type
        UniqueConstraint(
            "source_node_id", "target_node_id", "relationship_type",
            name="uq_graph_edge_src_tgt_type",
        ),
        # Self-loop guard at DB level
        CheckConstraint(
            "source_node_id <> target_node_id",
            name="ck_graph_edge_no_self_loop",
        ),
        Index("ix_graph_edge_org_rel", "organization_id", "relationship_type"),
        Index("ix_graph_edge_source", "source_node_id"),
        Index("ix_graph_edge_target", "target_node_id"),
        Index("ix_graph_edge_org_time", "organization_id", "created_at"),
    )

    def __repr__(self) -> str:
        return (
            f"<GraphEdge {self.source_node_id} --[{self.relationship_type}]--> "
            f"{self.target_node_id} conf={self.confidence_score:.2f}>"
        )
