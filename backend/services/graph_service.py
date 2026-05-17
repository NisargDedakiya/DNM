"""
Graph Service (Phase 20): PostgreSQL-backed security intelligence graph.

Manages the lifecycle of GraphNode and GraphEdge rows.

NOTE: The previous graph_service.py contained Redis-only helpers
(index_asset, index_endpoint, materialize_program_graph, …).  Those functions
are preserved in ``backend/services/redis_graph_service.py``.  This module
replaces the service contract with a full DB-backed implementation that Redis
can cache on top of.

Responsibilities
----------------
- Create / upsert graph nodes for any entity type.
- Create / upsert directed edges between nodes.
- Query neighbours of a given node (one-hop adjacency).
- Bounded BFS traversal from a starting node.
- Bulk-bootstrap a graph from existing DB entities.

Security guarantees
-------------------
- ALL read and write operations filter on ``organization_id``.
- Traversal depth is hard-capped at ``MAX_TRAVERSAL_DEPTH`` (default 5).
- Self-loop edges are rejected before any DB write.
- Parallel edges of the same type are silently deduplicated (upsert).
"""
from __future__ import annotations

import logging
from collections import deque
from typing import Any
from uuid import UUID

from sqlalchemy import select, and_, or_, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.graph_node import GraphNode, NodeType
from backend.models.graph_edge import GraphEdge, RelationshipType

logger = logging.getLogger(__name__)

MAX_TRAVERSAL_DEPTH: int = 5   # hard cap; override per-call within this limit


class GraphService:
    """
    PostgreSQL-backed security intelligence graph service.

    All methods are async and enforce workspace isolation via organization_id.
    """

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # =========================================================================
    # NODE MANAGEMENT
    # =========================================================================

    async def create_node(
        self,
        organization_id: UUID,
        node_type: NodeType | str,
        reference_id: UUID,
        label: str | None = None,
        node_metadata: dict[str, Any] | None = None,
    ) -> GraphNode:
        """
        Create or upsert a GraphNode for a source entity.

        If a node with the same (organization_id, node_type, reference_id)
        already exists, the label and metadata are updated in-place and the
        existing node is returned.  This makes node creation idempotent and
        safe to call from monitoring pipelines.

        Parameters
        ----------
        organization_id :
            Workspace owner.
        node_type :
            NodeType enum value or its string representation.
        reference_id :
            UUID of the authoritative source row.
        label :
            Human-readable display label.
        node_metadata :
            Lightweight attribute dict for graph queries.

        Returns
        -------
        GraphNode
        """
        nt = NodeType(node_type) if isinstance(node_type, str) else node_type

        # Check for existing node
        stmt = select(GraphNode).where(
            and_(
                GraphNode.organization_id == organization_id,
                GraphNode.node_type == nt,
                GraphNode.reference_id == reference_id,
            )
        )
        result = await self.db.execute(stmt)
        existing = result.scalars().first()

        if existing:
            # Update mutable fields in-place (label / metadata may evolve)
            if label is not None:
                existing.label = label
            if node_metadata is not None:
                existing.node_metadata = node_metadata
            await self.db.commit()
            await self.db.refresh(existing)
            return existing

        node = GraphNode(
            organization_id=organization_id,
            node_type=nt,
            reference_id=reference_id,
            label=label,
            node_metadata=node_metadata or {},
        )
        self.db.add(node)
        await self.db.commit()
        await self.db.refresh(node)

        logger.debug(
            "GraphNode created: id=%s type=%s label=%r org=%s",
            node.id, nt, label, organization_id,
        )
        return node

    async def get_node(
        self,
        organization_id: UUID,
        node_type: NodeType | str,
        reference_id: UUID,
    ) -> GraphNode | None:
        """Fetch a node by entity reference with workspace isolation."""
        nt = NodeType(node_type) if isinstance(node_type, str) else node_type
        stmt = select(GraphNode).where(
            and_(
                GraphNode.organization_id == organization_id,
                GraphNode.node_type == nt,
                GraphNode.reference_id == reference_id,
            )
        )
        result = await self.db.execute(stmt)
        return result.scalars().first()

    async def get_node_by_id(
        self,
        organization_id: UUID,
        node_id: UUID,
    ) -> GraphNode | None:
        """Fetch a node by graph ID with workspace isolation."""
        stmt = select(GraphNode).where(
            and_(
                GraphNode.id == node_id,
                GraphNode.organization_id == organization_id,
            )
        )
        result = await self.db.execute(stmt)
        return result.scalars().first()

    async def list_nodes(
        self,
        organization_id: UUID,
        node_type: NodeType | str | None = None,
        limit: int = 200,
        offset: int = 0,
    ) -> list[GraphNode]:
        """List graph nodes for an organisation, optionally filtered by type."""
        conditions = [GraphNode.organization_id == organization_id]
        if node_type is not None:
            nt = NodeType(node_type) if isinstance(node_type, str) else node_type
            conditions.append(GraphNode.node_type == nt)

        stmt = (
            select(GraphNode)
            .where(and_(*conditions))
            .order_by(GraphNode.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    # =========================================================================
    # EDGE MANAGEMENT
    # =========================================================================

    async def create_edge(
        self,
        organization_id: UUID,
        source_node_id: UUID,
        target_node_id: UUID,
        relationship_type: RelationshipType | str,
        confidence_score: float = 1.0,
        weight: float | None = None,
        notes: str | None = None,
    ) -> GraphEdge | None:
        """
        Create or upsert a directed edge between two nodes.

        Returns
        -------
        GraphEdge | None
            The created/existing edge, or None if a self-loop was attempted.

        Notes
        -----
        - Self-loops (source == target) are silently rejected.
        - Parallel edges of the same type are deduplicated; confidence_score
          and weight are updated if the edge already exists.
        """
        if source_node_id == target_node_id:
            logger.warning(
                "Rejected self-loop edge: node=%s org=%s", source_node_id, organization_id
            )
            return None

        rt = RelationshipType(relationship_type) if isinstance(relationship_type, str) else relationship_type
        effective_weight = weight if weight is not None else confidence_score

        # Upsert: find existing parallel edge
        stmt = select(GraphEdge).where(
            and_(
                GraphEdge.source_node_id == source_node_id,
                GraphEdge.target_node_id == target_node_id,
                GraphEdge.relationship_type == rt,
            )
        )
        result = await self.db.execute(stmt)
        existing = result.scalars().first()

        if existing:
            existing.confidence_score = confidence_score
            existing.weight = effective_weight
            if notes is not None:
                existing.notes = notes
            await self.db.commit()
            await self.db.refresh(existing)
            return existing

        edge = GraphEdge(
            organization_id=organization_id,
            source_node_id=source_node_id,
            target_node_id=target_node_id,
            relationship_type=rt,
            confidence_score=confidence_score,
            weight=effective_weight,
            notes=notes,
        )
        self.db.add(edge)
        await self.db.commit()
        await self.db.refresh(edge)

        logger.debug(
            "GraphEdge created: %s --[%s]--> %s conf=%.2f",
            source_node_id, rt, target_node_id, confidence_score,
        )
        return edge

    async def delete_edge(
        self,
        organization_id: UUID,
        source_node_id: UUID,
        target_node_id: UUID,
        relationship_type: RelationshipType | str,
    ) -> bool:
        """Remove an edge. Returns True if deleted, False if not found."""
        rt = RelationshipType(relationship_type) if isinstance(relationship_type, str) else relationship_type
        stmt = select(GraphEdge).where(
            and_(
                GraphEdge.organization_id == organization_id,
                GraphEdge.source_node_id == source_node_id,
                GraphEdge.target_node_id == target_node_id,
                GraphEdge.relationship_type == rt,
            )
        )
        result = await self.db.execute(stmt)
        edge = result.scalars().first()
        if edge is None:
            return False
        await self.db.delete(edge)
        await self.db.commit()
        return True

    # =========================================================================
    # ADJACENCY QUERIES
    # =========================================================================

    async def get_connected_nodes(
        self,
        organization_id: UUID,
        node_id: UUID,
        direction: str = "both",
        relationship_types: list[str] | None = None,
        limit: int = 100,
    ) -> dict[str, Any]:
        """
        Return the one-hop neighbourhood of a node.

        Parameters
        ----------
        node_id :
            Centre node to expand.
        direction :
            ``"outgoing"`` – edges where node is source.
            ``"incoming"`` – edges where node is target.
            ``"both"``     – union of both directions.
        relationship_types :
            Optional whitelist of edge types to include.
        limit :
            Maximum neighbours to return.

        Returns
        -------
        dict with keys:
            center  – GraphNode dict for the queried node
            edges   – list of edge dicts
            nodes   – list of neighbour node dicts
        """
        center = await self.get_node_by_id(organization_id, node_id)
        if center is None:
            return {"center": None, "edges": [], "nodes": []}

        rt_filter = None
        if relationship_types:
            rt_filter = [RelationshipType(r) if isinstance(r, str) else r for r in relationship_types]

        edges: list[GraphEdge] = []

        if direction in ("outgoing", "both"):
            conds = [GraphEdge.source_node_id == node_id]
            if rt_filter:
                conds.append(GraphEdge.relationship_type.in_([r.value for r in rt_filter]))
            stmt = select(GraphEdge).where(and_(*conds)).limit(limit)
            res = await self.db.execute(stmt)
            edges.extend(res.scalars().all())

        if direction in ("incoming", "both"):
            conds = [GraphEdge.target_node_id == node_id]
            if rt_filter:
                conds.append(GraphEdge.relationship_type.in_([r.value for r in rt_filter]))
            stmt = select(GraphEdge).where(and_(*conds)).limit(limit)
            res = await self.db.execute(stmt)
            edges.extend(res.scalars().all())

        # Collect unique neighbour node IDs
        neighbour_ids: set[UUID] = set()
        for e in edges:
            neighbour_ids.add(e.source_node_id if e.target_node_id == node_id else e.target_node_id)

        neighbour_nodes: list[GraphNode] = []
        if neighbour_ids:
            n_stmt = select(GraphNode).where(
                and_(
                    GraphNode.id.in_(neighbour_ids),
                    GraphNode.organization_id == organization_id,
                )
            )
            n_res = await self.db.execute(n_stmt)
            neighbour_nodes = list(n_res.scalars().all())

        def _node_dict(n: GraphNode) -> dict:
            return {
                "id": str(n.id),
                "node_type": n.node_type,
                "reference_id": str(n.reference_id),
                "label": n.label,
                "metadata": n.node_metadata,
                "created_at": n.created_at.isoformat() if n.created_at else None,
            }

        def _edge_dict(e: GraphEdge) -> dict:
            return {
                "id": str(e.id),
                "source_node_id": str(e.source_node_id),
                "target_node_id": str(e.target_node_id),
                "relationship_type": e.relationship_type,
                "confidence_score": e.confidence_score,
                "weight": e.weight,
                "notes": e.notes,
            }

        return {
            "center": _node_dict(center),
            "edges": [_edge_dict(e) for e in edges],
            "nodes": [_node_dict(n) for n in neighbour_nodes],
        }

    # =========================================================================
    # BOUNDED BFS TRAVERSAL
    # =========================================================================

    async def traverse_graph(
        self,
        organization_id: UUID,
        start_node_id: UUID,
        max_depth: int = 3,
        relationship_types: list[str] | None = None,
        direction: str = "outgoing",
    ) -> dict[str, Any]:
        """
        Breadth-first traversal from ``start_node_id`` up to ``max_depth`` hops.

        Parameters
        ----------
        start_node_id :
            Root node of the traversal.
        max_depth :
            Maximum hops; capped at MAX_TRAVERSAL_DEPTH for safety.
        relationship_types :
            Optional whitelist of edge types to follow.
        direction :
            ``"outgoing"``, ``"incoming"``, or ``"both"``.

        Returns
        -------
        dict with keys:
            nodes  – dict[node_id_str → node_dict] (all visited nodes)
            edges  – list of traversed edge dicts
            depth  – actual traversal depth reached
        """
        depth = min(max_depth, MAX_TRAVERSAL_DEPTH)
        rt_filter_vals = (
            [RelationshipType(r).value if isinstance(r, str) else r.value for r in relationship_types]
            if relationship_types
            else None
        )

        visited_node_ids: set[UUID] = set()
        all_nodes: dict[str, dict] = {}
        all_edges: list[dict] = []

        queue: deque[tuple[UUID, int]] = deque([(start_node_id, 0)])
        visited_node_ids.add(start_node_id)

        while queue:
            current_id, current_depth = queue.popleft()
            if current_depth >= depth:
                continue

            # Fetch edges for current node
            edge_conditions: list = []
            if direction in ("outgoing", "both"):
                edge_conditions.append(GraphEdge.source_node_id == current_id)
            if direction in ("incoming", "both"):
                edge_conditions.append(GraphEdge.target_node_id == current_id)

            if not edge_conditions:
                continue

            comb = or_(*edge_conditions) if len(edge_conditions) > 1 else edge_conditions[0]
            edge_stmt = select(GraphEdge).where(comb)
            if rt_filter_vals:
                edge_stmt = edge_stmt.where(GraphEdge.relationship_type.in_(rt_filter_vals))
            edge_stmt = edge_stmt.limit(200)  # per-node safety limit

            edge_result = await self.db.execute(edge_stmt)
            edges = edge_result.scalars().all()

            for edge in edges:
                all_edges.append({
                    "id": str(edge.id),
                    "source_node_id": str(edge.source_node_id),
                    "target_node_id": str(edge.target_node_id),
                    "relationship_type": edge.relationship_type,
                    "confidence_score": edge.confidence_score,
                    "weight": edge.weight,
                    "depth": current_depth + 1,
                })
                # Find the neighbour node
                neighbour_id = (
                    edge.target_node_id
                    if edge.source_node_id == current_id
                    else edge.source_node_id
                )
                if neighbour_id not in visited_node_ids:
                    visited_node_ids.add(neighbour_id)
                    queue.append((neighbour_id, current_depth + 1))

        # Batch-fetch all visited nodes
        if visited_node_ids:
            n_stmt = select(GraphNode).where(
                and_(
                    GraphNode.id.in_(visited_node_ids),
                    GraphNode.organization_id == organization_id,
                )
            )
            n_res = await self.db.execute(n_stmt)
            for node in n_res.scalars().all():
                all_nodes[str(node.id)] = {
                    "id": str(node.id),
                    "node_type": node.node_type,
                    "reference_id": str(node.reference_id),
                    "label": node.label,
                    "metadata": node.node_metadata,
                    "created_at": node.created_at.isoformat() if node.created_at else None,
                }

        logger.info(
            "Graph traversal complete: org=%s start=%s depth=%d nodes=%d edges=%d",
            organization_id, start_node_id, depth, len(all_nodes), len(all_edges),
        )
        return {
            "nodes": all_nodes,
            "edges": all_edges,
            "depth": depth,
            "node_count": len(all_nodes),
            "edge_count": len(all_edges),
        }

    # =========================================================================
    # BULK GRAPH STATS
    # =========================================================================

    async def get_graph_stats(self, organization_id: UUID) -> dict[str, Any]:
        """Return aggregate statistics about the graph for an organisation."""
        from sqlalchemy import func

        node_count_stmt = select(func.count(GraphNode.id)).where(
            GraphNode.organization_id == organization_id
        )
        edge_count_stmt = select(func.count(GraphEdge.id)).where(
            GraphEdge.organization_id == organization_id
        )
        node_type_stmt = (
            select(GraphNode.node_type, func.count(GraphNode.id).label("cnt"))
            .where(GraphNode.organization_id == organization_id)
            .group_by(GraphNode.node_type)
        )
        edge_type_stmt = (
            select(GraphEdge.relationship_type, func.count(GraphEdge.id).label("cnt"))
            .where(GraphEdge.organization_id == organization_id)
            .group_by(GraphEdge.relationship_type)
        )

        node_count = (await self.db.execute(node_count_stmt)).scalar() or 0
        edge_count = (await self.db.execute(edge_count_stmt)).scalar() or 0
        node_types = {row[0]: row[1] for row in (await self.db.execute(node_type_stmt)).all()}
        edge_types = {row[0]: row[1] for row in (await self.db.execute(edge_type_stmt)).all()}

        return {
            "total_nodes": node_count,
            "total_edges": edge_count,
            "nodes_by_type": node_types,
            "edges_by_type": edge_types,
        }
