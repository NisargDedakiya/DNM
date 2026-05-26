"""
Visibility restrictions for confidential findings and attack graphs.
"""
from __future__ import annotations

from typing import Any


def restrict_finding_visibility(finding: dict[str, Any]) -> dict[str, Any]:
    sanitized = dict(finding)
    sanitized.pop("raw_payload", None)
    sanitized.pop("secret", None)
    sanitized["visibility"] = "restricted"
    sanitized["confidential"] = True
    return sanitized


def isolate_attack_graph(graph_payload: dict[str, Any]) -> dict[str, Any]:
    nodes = [node for node in graph_payload.get("nodes", []) if not node.get("restricted") is False]
    edges = [edge for edge in graph_payload.get("edges", []) if edge.get("visibility", "restricted") != "public"]
    return {
        "nodes": nodes,
        "edges": edges,
        "visibility": "restricted",
        "confidential": True,
    }


def hide_sensitive_assets(assets: list[dict[str, Any]]) -> list[dict[str, Any]]:
    hidden: list[dict[str, Any]] = []
    for asset in assets:
        sanitized = dict(asset)
        if sanitized.get("sensitivity") in {"secret", "confidential", "private"}:
            sanitized["name"] = "Restricted Asset"
            sanitized["ip_address"] = None
            sanitized["visibility"] = "hidden"
        hidden.append(sanitized)
    return hidden
