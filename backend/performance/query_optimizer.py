"""
Query planning helpers for reducing database load and N+1 patterns.
"""
from __future__ import annotations

from typing import Any


def optimize_finding_queries(filters: dict[str, Any] | None = None) -> dict[str, Any]:
    filters = filters or {}
    severity = filters.get("severity")
    include_related = bool(filters.get("include_related", True))
    limit = min(int(filters.get("limit", 100)), 500)
    return {
        "domain": "findings",
        "organization_id": filters.get("organization_id"),
        "limit": limit,
        "use_eager_loading": include_related,
        "prefetch_relationships": ["asset", "exposure", "technology"] if include_related else [],
        "batch_size": 50 if limit > 50 else limit,
        "join_strategy": "selectinload",
        "index_hints": ["organization_id", "severity", "created_at"],
        "filter_plan": {"severity": severity, "status": filters.get("status")},
        "cache_ttl_seconds": 120 if severity else 60,
    }


def optimize_graph_queries(filters: dict[str, Any] | None = None) -> dict[str, Any]:
    filters = filters or {}
    depth = min(int(filters.get("depth", 2)), 4)
    node_limit = min(int(filters.get("node_limit", 150)), 500)
    return {
        "domain": "graph",
        "organization_id": filters.get("organization_id"),
        "traversal_depth": depth,
        "node_limit": node_limit,
        "edge_limit": min(int(filters.get("edge_limit", 300)), 1000),
        "use_projection": True,
        "prune_low_signal_nodes": True,
        "render_batch_size": 25,
        "relationship_filters": filters.get("relationship_filters", ["affects", "related_to", "exposed_by"]),
        "cache_ttl_seconds": 90,
    }


def optimize_historical_lookups(filters: dict[str, Any] | None = None) -> dict[str, Any]:
    filters = filters or {}
    window_days = min(int(filters.get("window_days", 30)), 365)
    return {
        "domain": "historical",
        "organization_id": filters.get("organization_id"),
        "window_days": window_days,
        "summary_first": True,
        "page_size": min(int(filters.get("page_size", 100)), 500),
        "order_by": filters.get("order_by", "created_at desc"),
        "cache_ttl_seconds": 180,
        "index_hints": ["organization_id", "created_at", "updated_at"],
        "rollup_windows": ["24h", "7d", "30d"],
    }
