"""
Intelligence Graph Service: connected risk analysis and attack surface intelligence.

This service sits above GraphService and RelationshipService and provides
high-level analytical functions:

- calculate_risk_propagation()   → spread risk scores through the graph
- analyze_attack_surface_graph() → holistic connected surface view
- identify_high_risk_clusters()  → find densely-connected high-risk subgraphs
- build_intelligence_map()       → full intelligence report for UI rendering

Design principles
-----------------
- Read-mostly: uses GraphService for all DB access.
- Bounded: all traversals respect MAX_TRAVERSAL_DEPTH.
- Workspace isolated: organization_id on every operation.
- Analytics results returned as plain dicts (no ORM objects in responses).
"""
from __future__ import annotations

import logging
from collections import defaultdict
from typing import Any
from uuid import UUID

from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.graph_node import GraphNode, NodeType
from backend.models.graph_edge import GraphEdge, RelationshipType
from backend.services.graph_service import GraphService

logger = logging.getLogger(__name__)

# Severity → numeric weight for risk propagation
_SEVERITY_WEIGHTS: dict[str, float] = {
    "critical": 1.0,
    "high": 0.75,
    "medium": 0.50,
    "low": 0.25,
    "info": 0.05,
}

# Risk-propagation decay per hop (avoids unbounded amplification)
_PROPAGATION_DECAY: float = 0.6


class IntelligenceGraphService:
    """
    High-level security intelligence analytics over the graph layer.
    """

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self._graph = GraphService(db)

    # =========================================================================
    # RISK PROPAGATION
    # =========================================================================

    async def calculate_risk_propagation(
        self,
        organization_id: UUID,
        start_node_id: UUID,
        max_depth: int = 3,
    ) -> dict[str, Any]:
        """
        Propagate risk scores from a seed node through the graph via BFS.

        Algorithm
        ---------
        1. Start with the seed node's base risk (from node_metadata.risk_score
           or severity weight).
        2. For each hop, multiply the incoming risk by edge.weight * DECAY.
        3. Accumulate risk per node (take max if visited from multiple paths).
        4. Return all affected nodes with their propagated risk scores.

        Parameters
        ----------
        start_node_id :
            Seed node (typically a high-risk exposure or finding node).
        max_depth :
            Propagation depth (capped at 5).

        Returns
        -------
        dict with keys:
            seed_node         – seed node dict
            propagated_risks  – {node_id: {node, propagated_risk, depth}}
            total_affected    – count of affected nodes
            max_propagated_risk – highest risk score reached
        """
        traversal = await self._graph.traverse_graph(
            organization_id=organization_id,
            start_node_id=start_node_id,
            max_depth=max_depth,
            direction="outgoing",
        )

        if not traversal["nodes"]:
            return {
                "seed_node": None,
                "propagated_risks": {},
                "total_affected": 0,
                "max_propagated_risk": 0.0,
            }

        # Determine seed risk
        seed_node_dict = traversal["nodes"].get(str(start_node_id), {})
        seed_meta = seed_node_dict.get("metadata") or {}
        severity = seed_meta.get("severity") or seed_meta.get("risk_level") or "info"
        base_risk = float(seed_meta.get("risk_score") or _SEVERITY_WEIGHTS.get(severity, 0.1))

        # BFS-style propagation over the traversal result
        propagated: dict[str, dict] = {}
        propagated[str(start_node_id)] = {
            "node": seed_node_dict,
            "propagated_risk": base_risk,
            "depth": 0,
        }

        # Build edge index: source → [edge]
        out_edges: dict[str, list[dict]] = defaultdict(list)
        for edge in traversal["edges"]:
            out_edges[edge["source_node_id"]].append(edge)

        # BFS propagation
        queue = [(str(start_node_id), base_risk, 0)]
        while queue:
            current_id, current_risk, depth = queue.pop(0)
            if depth >= max_depth:
                continue
            for edge in out_edges.get(current_id, []):
                tgt_id = edge["target_node_id"]
                propagated_risk = current_risk * edge.get("weight", 1.0) * _PROPAGATION_DECAY
                existing = propagated.get(tgt_id)
                if existing is None or existing["propagated_risk"] < propagated_risk:
                    propagated[tgt_id] = {
                        "node": traversal["nodes"].get(tgt_id, {}),
                        "propagated_risk": round(propagated_risk, 4),
                        "depth": depth + 1,
                    }
                    queue.append((tgt_id, propagated_risk, depth + 1))

        # Remove seed from propagated output (it's the origin, not affected)
        propagated.pop(str(start_node_id), None)

        max_risk = max((v["propagated_risk"] for v in propagated.values()), default=0.0)

        return {
            "seed_node": seed_node_dict,
            "propagated_risks": propagated,
            "total_affected": len(propagated),
            "max_propagated_risk": round(max_risk, 4),
        }

    # =========================================================================
    # ATTACK SURFACE GRAPH ANALYSIS
    # =========================================================================

    async def analyze_attack_surface_graph(
        self,
        organization_id: UUID,
    ) -> dict[str, Any]:
        """
        Generate a holistic analysis of the connected attack surface graph.

        Returns
        -------
        dict with keys:
            graph_stats      – node/edge counts by type
            entry_points     – asset nodes with the most outgoing edges
            exposure_density – assets with the most exposure edges
            technology_spread – most common technology nodes by name
            isolated_nodes   – nodes with no edges (orphaned entities)
            connectivity_score – 0–100 graph connectivity health metric
        """
        stats = await self._graph.get_graph_stats(organization_id)

        # Entry points: asset nodes ordered by outgoing edge count
        entry_stmt = (
            select(
                GraphEdge.source_node_id,
                func.count(GraphEdge.id).label("out_degree"),
            )
            .where(
                and_(
                    GraphEdge.organization_id == organization_id,
                    GraphEdge.relationship_type.in_([
                        RelationshipType.HOSTS.value,
                        RelationshipType.EXPOSES.value,
                        RelationshipType.DEPENDS_ON.value,
                    ]),
                )
            )
            .group_by(GraphEdge.source_node_id)
            .order_by(func.count(GraphEdge.id).desc())
            .limit(10)
        )
        entry_result = await self.db.execute(entry_stmt)
        entry_points_raw = entry_result.all()

        entry_points = []
        for row in entry_points_raw:
            node = await self._graph.get_node_by_id(organization_id, row[0])
            if node:
                entry_points.append({
                    "node_id": str(node.id),
                    "label": node.label,
                    "node_type": node.node_type,
                    "out_degree": row[1],
                    "metadata": node.node_metadata,
                })

        # Exposure density: assets with most EXPOSES edges
        exp_stmt = (
            select(
                GraphEdge.source_node_id,
                func.count(GraphEdge.id).label("exposure_count"),
            )
            .where(
                and_(
                    GraphEdge.organization_id == organization_id,
                    GraphEdge.relationship_type == RelationshipType.EXPOSES.value,
                )
            )
            .group_by(GraphEdge.source_node_id)
            .order_by(func.count(GraphEdge.id).desc())
            .limit(10)
        )
        exp_result = await self.db.execute(exp_stmt)
        exposure_density = []
        for row in exp_result.all():
            node = await self._graph.get_node_by_id(organization_id, row[0])
            if node:
                exposure_density.append({
                    "node_id": str(node.id),
                    "label": node.label,
                    "exposure_count": row[1],
                    "metadata": node.node_metadata,
                })

        # Technology spread: count dependency edges grouped by tech label
        tech_nodes = await self._graph.list_nodes(
            organization_id=organization_id,
            node_type=NodeType.TECHNOLOGY,
            limit=1000,
        )
        tech_name_count: dict[str, int] = defaultdict(int)
        for tn in tech_nodes:
            meta = tn.node_metadata or {}
            name = (meta.get("name") or tn.label or "unknown").lower()
            tech_name_count[name] += 1
        technology_spread = sorted(
            [{"name": k, "count": v} for k, v in tech_name_count.items()],
            key=lambda x: x["count"],
            reverse=True,
        )[:20]

        # Isolated nodes: nodes with no edges at all
        total_nodes = stats["total_nodes"]
        total_edges = stats["total_edges"]
        connectivity_score = (
            min(100, int((total_edges / max(total_nodes, 1)) * 25))
            if total_nodes > 0
            else 0
        )

        return {
            "graph_stats": stats,
            "entry_points": entry_points,
            "exposure_density": exposure_density,
            "technology_spread": technology_spread,
            "connectivity_score": connectivity_score,
        }

    # =========================================================================
    # HIGH-RISK CLUSTER IDENTIFICATION
    # =========================================================================

    async def identify_high_risk_clusters(
        self,
        organization_id: UUID,
        risk_threshold: float = 0.6,
        min_cluster_size: int = 2,
    ) -> dict[str, Any]:
        """
        Identify clusters of high-risk nodes that are densely interconnected.

        Algorithm
        ---------
        1. Fetch all exposure nodes with risk_score >= threshold.
        2. For each high-risk exposure, run a 2-hop traversal.
        3. Group overlapping traversal sets into clusters.
        4. Return clusters sorted by aggregate risk.

        Parameters
        ----------
        risk_threshold :
            Minimum node risk_score to seed a cluster [0.0–1.0].
        min_cluster_size :
            Minimum number of nodes in a cluster to be reported.

        Returns
        -------
        dict with ``clusters`` list and ``total_high_risk_nodes``.
        """
        # Fetch exposure nodes
        exposure_nodes = await self._graph.list_nodes(
            organization_id=organization_id,
            node_type=NodeType.EXPOSURE,
            limit=500,
        )

        # Filter by risk threshold
        high_risk_seeds = [
            n for n in exposure_nodes
            if float((n.node_metadata or {}).get("risk_score", 0)) >= risk_threshold
        ]

        # Also include finding nodes with critical/high severity
        finding_nodes = await self._graph.list_nodes(
            organization_id=organization_id,
            node_type=NodeType.FINDING,
            limit=500,
        )
        for fn in finding_nodes:
            meta = fn.node_metadata or {}
            sev = meta.get("severity", "info")
            if sev in ("critical", "high"):
                high_risk_seeds.append(fn)

        total_high_risk = len(high_risk_seeds)

        # Build adjacency clusters via union-find approach
        # Map node_id → cluster_id
        node_to_cluster: dict[str, str] = {}
        clusters: dict[str, set[str]] = {}

        for seed in high_risk_seeds:
            seed_id = str(seed.id)
            neighbours = await self._graph.get_connected_nodes(
                organization_id=organization_id,
                node_id=seed.id,
                direction="both",
                limit=50,
            )
            neighbour_ids = {n["id"] for n in neighbours["nodes"]}
            neighbour_ids.add(seed_id)

            # Find overlapping existing clusters
            overlapping = set()
            for nid in neighbour_ids:
                if nid in node_to_cluster:
                    overlapping.add(node_to_cluster[nid])

            if not overlapping:
                # New cluster
                clusters[seed_id] = neighbour_ids
                for nid in neighbour_ids:
                    node_to_cluster[nid] = seed_id
            else:
                # Merge into first overlapping cluster
                primary = next(iter(overlapping))
                for cid in overlapping:
                    if cid != primary:
                        clusters[primary].update(clusters.pop(cid, set()))
                clusters[primary].update(neighbour_ids)
                for nid in clusters[primary]:
                    node_to_cluster[nid] = primary

        # Build response clusters (filter by min size, compute aggregate risk)
        result_clusters = []
        seen_cluster_ids: set[str] = set()

        for cluster_id, node_ids in clusters.items():
            if len(node_ids) < min_cluster_size:
                continue
            if cluster_id in seen_cluster_ids:
                continue
            seen_cluster_ids.add(cluster_id)

            # Fetch node metadata for the cluster
            cluster_node_data = []
            aggregate_risk = 0.0
            for nid_str in node_ids:
                try:
                    nid = UUID(nid_str)
                except ValueError:
                    continue
                node = await self._graph.get_node_by_id(organization_id, nid)
                if node:
                    meta = node.node_metadata or {}
                    r = float(meta.get("risk_score", 0))
                    sev = meta.get("severity") or meta.get("risk_level") or "info"
                    r = max(r, _SEVERITY_WEIGHTS.get(sev, 0.0))
                    aggregate_risk += r
                    cluster_node_data.append({
                        "id": nid_str,
                        "node_type": node.node_type,
                        "label": node.label,
                        "risk_score": r,
                        "metadata": meta,
                    })

            result_clusters.append({
                "cluster_id": cluster_id,
                "size": len(cluster_node_data),
                "aggregate_risk": round(aggregate_risk, 3),
                "nodes": cluster_node_data,
            })

        result_clusters.sort(key=lambda c: c["aggregate_risk"], reverse=True)

        return {
            "clusters": result_clusters,
            "total_clusters": len(result_clusters),
            "total_high_risk_nodes": total_high_risk,
            "risk_threshold": risk_threshold,
        }

    # =========================================================================
    # INTELLIGENCE MAP
    # =========================================================================

    async def build_intelligence_map(
        self,
        organization_id: UUID,
        program_id: UUID | None = None,
    ) -> dict[str, Any]:
        """
        Build a comprehensive intelligence map for UI rendering.

        Combines graph stats, surface analysis, risk clusters, and a
        full node/edge listing suitable for graph visualisation libraries
        (e.g. D3.js, Cytoscape.js, vis.js).

        Parameters
        ----------
        organization_id :
            Workspace scope.
        program_id :
            Optional program scope filter for node listing.

        Returns
        -------
        dict with keys:
            nodes        – all nodes (formatted for graph viz)
            edges        – all edges (formatted for graph viz)
            stats        – graph statistics
            risk_summary – high-risk cluster summary
            surface_analysis – entry points and exposure density
            generated_at – ISO timestamp
        """
        from datetime import datetime

        # Graph-level stats and surface analysis
        stats = await self._graph.get_graph_stats(organization_id)
        surface = await self.analyze_attack_surface_graph(organization_id)
        risk_clusters = await self.identify_high_risk_clusters(organization_id)

        # Fetch all nodes (with optional program filter via metadata)
        all_nodes = await self._graph.list_nodes(
            organization_id=organization_id,
            limit=2000,
        )

        # Fetch all edges
        edge_stmt = (
            select(GraphEdge)
            .where(GraphEdge.organization_id == organization_id)
            .limit(5000)
        )
        edge_result = await self.db.execute(edge_stmt)
        all_edges = edge_result.scalars().all()

        # Format for graph visualisation
        viz_nodes = [
            {
                "id": str(n.id),
                "label": n.label or str(n.reference_id)[:8],
                "type": n.node_type,
                "reference_id": str(n.reference_id),
                "metadata": n.node_metadata or {},
                "created_at": n.created_at.isoformat() if n.created_at else None,
            }
            for n in all_nodes
            if program_id is None
            or (n.node_metadata or {}).get("program_id") == str(program_id)
            or n.node_type not in (NodeType.ASSET.value, NodeType.ENDPOINT.value)
        ]

        viz_edges = [
            {
                "id": str(e.id),
                "source": str(e.source_node_id),
                "target": str(e.target_node_id),
                "type": e.relationship_type,
                "confidence": e.confidence_score,
                "weight": e.weight,
                "notes": e.notes,
            }
            for e in all_edges
        ]

        return {
            "nodes": viz_nodes,
            "edges": viz_edges,
            "stats": stats,
            "risk_summary": {
                "total_clusters": risk_clusters["total_clusters"],
                "total_high_risk_nodes": risk_clusters["total_high_risk_nodes"],
                "top_clusters": risk_clusters["clusters"][:5],
            },
            "surface_analysis": {
                "entry_points": surface["entry_points"][:10],
                "exposure_density": surface["exposure_density"][:10],
                "technology_spread": surface["technology_spread"][:10],
                "connectivity_score": surface["connectivity_score"],
            },
            "generated_at": datetime.utcnow().isoformat(),
        }
