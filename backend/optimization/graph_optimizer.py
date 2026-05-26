"""
Graph payload trimming and signal prioritization helpers.
"""
from __future__ import annotations

from typing import Any


def optimize_graph_payload(payload: dict[str, Any] | None) -> dict[str, Any]:
    payload = payload or {}
    nodes = list(payload.get("nodes", []))
    edges = list(payload.get("edges", []))
    prioritized_nodes = prioritize_high_signal_nodes(nodes)
    reduced_nodes = reduce_node_density(prioritized_nodes, max_nodes=min(int(payload.get("max_nodes", 120)), 500))
    node_ids = {str(node.get("id") or node.get("node_id")) for node in reduced_nodes}
    reduced_edges = [edge for edge in edges if str(edge.get("source")) in node_ids and str(edge.get("target")) in node_ids]
    density = len(reduced_edges) / max(1, len(reduced_nodes))
    return {
        "nodes": reduced_nodes,
        "edges": reduced_edges,
        "node_count": len(reduced_nodes),
        "edge_count": len(reduced_edges),
        "node_density": round(density, 3),
        "render_budget": min(250, len(reduced_nodes) * 2),
        "recommendations": [
            "cluster related nodes",
            "lazy-load distant branches",
            "hide low-signal telemetry nodes",
        ],
    }


def reduce_node_density(nodes: list[dict[str, Any]], max_nodes: int = 150) -> list[dict[str, Any]]:
    ranked = sorted(nodes, key=_node_score, reverse=True)
    return ranked[:max(1, int(max_nodes))]


def prioritize_high_signal_nodes(nodes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(nodes, key=_node_score, reverse=True)


def _node_score(node: dict[str, Any]) -> float:
    severity_weight = {
        "critical": 5.0,
        "high": 4.0,
        "medium": 3.0,
        "low": 2.0,
        "info": 1.0,
    }
    risk_score = float(node.get("risk_score", 0.0) or 0.0)
    severity = str(node.get("severity") or node.get("priority") or "info").lower()
    recency = float(node.get("recent_activity_score", 0.0) or 0.0)
    degree = float(node.get("degree", 0.0) or 0.0)
    return risk_score * 2 + severity_weight.get(severity, 1.0) + recency + (degree / 10.0)
