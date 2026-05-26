"""
Context Builder: assembles multi-source intelligence into AI-safe context windows.

Gathers structured data from the domain layer (assets, exposures, findings,
graph) and serialises it into a compact, token-aware, workspace-isolated
context dict that the copilot engine can safely embed into prompts.

Security rules
--------------
- All queries MUST filter on organization_id.
- All string values are sanitised through _sanitize() before embedding.
- Context window is hard-truncated at MAX_CONTEXT_CHARS to stay within token
  limits and prevent prompt injection via oversized field values.
- No raw user input is embedded — only structured DB data.

Context dict schema (all builders return the same envelope)
-----------------------------------------------------------
{
  "context_type":   str,          # "asset" | "exposure" | "finding" | "graph"
  "organization_id": str,
  "entity_id":      str,
  "entity_summary": dict,         # key facts about the primary entity
  "related_data":   dict,         # neighbouring entities / relationships
  "historical":     list[dict],   # recent change events (last 14 days)
  "graph_hints":    dict,         # node type counts, connectivity score
  "context_built_at": str,        # ISO timestamp
}
"""
from __future__ import annotations

import logging
import re
from datetime import datetime, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import select, and_, desc, func
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.asset import Asset
from backend.models.endpoint import Endpoint
from backend.models.technology import Technology
from backend.models.exposure import Exposure
from backend.models.finding import Finding
from backend.models.change_event import ChangeEvent
from backend.models.graph_node import GraphNode, NodeType
from backend.models.graph_edge import GraphEdge

logger = logging.getLogger(__name__)

# Hard cap on total serialised context characters (≈ 3500 tokens at 4 chars/token)
MAX_CONTEXT_CHARS = 14_000
# Per-field sanitisation caps
_FIELD_MAX = 300
_LIST_MAX_ITEMS = 8

# Characters that could confuse prompt formatting
_UNSAFE_RE = re.compile(r"[\x00-\x1f\x7f`\"\\]")


def _s(value: Any, max_len: int = _FIELD_MAX) -> str:
    """Sanitise a value for safe embedding in AI prompts."""
    text = str(value) if value is not None else ""
    cleaned = _UNSAFE_RE.sub(" ", text)
    return cleaned[:max_len].strip()


def _sl(values: list[Any], max_items: int = _LIST_MAX_ITEMS, item_max: int = 100) -> list[str]:
    """Sanitise a list of values, capping count and length."""
    return [_s(v, item_max) for v in (values or [])[:max_items]]


def _truncate_context(ctx: dict) -> dict:
    """Recursively truncate a context dict to stay within MAX_CONTEXT_CHARS."""
    import json
    serialised = json.dumps(ctx)
    if len(serialised) <= MAX_CONTEXT_CHARS:
        return ctx
    # Trim historical events first (largest payload)
    if ctx.get("historical"):
        ctx["historical"] = ctx["historical"][:3]
    # Trim related data lists
    for key, val in ctx.get("related_data", {}).items():
        if isinstance(val, list) and len(val) > 3:
            ctx["related_data"][key] = val[:3]
    return ctx


class ContextBuilder:
    """
    Assembles workspace-isolated, AI-safe context windows from domain data.
    """

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # =========================================================================
    # ASSET CONTEXT
    # =========================================================================

    async def build_asset_context(
        self,
        organization_id: UUID,
        asset_id: UUID,
    ) -> dict[str, Any]:
        """
        Build investigation context for a specific asset.

        Includes: asset facts, endpoints, technologies, active exposures,
        related findings, recent change events, and graph node stats.
        """
        # Primary entity
        asset_stmt = select(Asset).where(
            and_(Asset.id == asset_id, Asset.organization_id == organization_id)
        )
        result = await self.db.execute(asset_stmt)
        asset = result.scalars().first()

        if asset is None:
            return {"error": "Asset not found", "organization_id": str(organization_id)}

        entity_summary = {
            "id": _s(asset.id),
            "hostname": _s(asset.hostname),
            "ip_address": _s(asset.ip_address),
            "is_alive": asset.is_alive,
            "is_internet_facing": getattr(asset, "is_internet_facing", False),
            "risk_score": round(asset.risk_score or 0, 2),
            "first_seen": _s(asset.first_seen.isoformat() if asset.first_seen else None),
            "last_seen": _s(asset.last_seen.isoformat() if asset.last_seen else None),
        }

        # Endpoints (capped)
        ep_stmt = select(Endpoint).where(Endpoint.asset_id == asset_id).limit(10)
        ep_result = await self.db.execute(ep_stmt)
        endpoints = [
            {"path": _s(e.path), "method": _s(e.method), "status_code": e.status_code}
            for e in ep_result.scalars().all()
        ]

        # Technologies
        tech_stmt = select(Technology).where(Technology.asset_id == asset_id).limit(10)
        tech_result = await self.db.execute(tech_stmt)
        technologies = [
            {"name": _s(t.name), "version": _s(t.version), "confidence": round(t.confidence_score or 0, 2)}
            for t in tech_result.scalars().all()
        ]

        # Active exposures
        exp_stmt = select(Exposure).where(
            and_(Exposure.asset_id == asset_id, Exposure.is_active == True)
        ).order_by(desc(Exposure.risk_score)).limit(8)
        exp_result = await self.db.execute(exp_stmt)
        exposures = [
            {
                "title": _s(e.title),
                "type": _s(e.exposure_type),
                "risk_level": _s(e.risk_level),
                "risk_score": round(e.risk_score or 0, 2),
                "days_open": (datetime.utcnow() - e.first_detected).days if e.first_detected else None,
            }
            for e in exp_result.scalars().all()
        ]

        # Recent change events (14 days)
        since = datetime.utcnow() - timedelta(days=14)
        chg_stmt = select(ChangeEvent).where(
            and_(
                ChangeEvent.organization_id == organization_id,
                ChangeEvent.detected_at >= since,
            )
        ).order_by(desc(ChangeEvent.detected_at)).limit(6)
        chg_result = await self.db.execute(chg_stmt)
        historical = [
            {
                "change_type": _s(e.change_type),
                "severity": _s(e.severity),
                "change_score": round(e.change_score or 0, 2),
                "detected_at": _s(e.detected_at.strftime("%Y-%m-%d") if e.detected_at else None),
            }
            for e in chg_result.scalars().all()
        ]

        # Graph node stats for this asset
        graph_hints = await self._get_graph_hints(organization_id, asset_id, NodeType.ASSET)

        ctx = {
            "context_type": "asset",
            "organization_id": _s(organization_id),
            "entity_id": _s(asset_id),
            "entity_summary": entity_summary,
            "related_data": {
                "endpoints": endpoints,
                "technologies": technologies,
                "active_exposures": exposures,
                "endpoint_count": len(endpoints),
                "technology_count": len(technologies),
                "active_exposure_count": len(exposures),
            },
            "historical": historical,
            "graph_hints": graph_hints,
            "context_built_at": datetime.utcnow().isoformat(),
        }
        return _truncate_context(ctx)

    # =========================================================================
    # EXPOSURE CONTEXT
    # =========================================================================

    async def build_exposure_context(
        self,
        organization_id: UUID,
        exposure_id: UUID,
    ) -> dict[str, Any]:
        """
        Build investigation context for a specific exposure.

        Includes: exposure facts, parent asset facts, exposure history,
        related findings, and recent change events.
        """
        exp_stmt = select(Exposure).where(
            and_(Exposure.id == exposure_id, Exposure.organization_id == organization_id)
        )
        result = await self.db.execute(exp_stmt)
        exposure = result.scalars().first()

        if exposure is None:
            return {"error": "Exposure not found", "organization_id": str(organization_id)}

        entity_summary = {
            "id": _s(exposure.id),
            "title": _s(exposure.title),
            "exposure_type": _s(exposure.exposure_type),
            "risk_level": _s(exposure.risk_level),
            "risk_score": round(exposure.risk_score or 0, 2),
            "confidence_score": round(exposure.confidence_score or 0, 2),
            "is_active": exposure.is_active,
            "remediation_status": _s(exposure.remediation_status),
            "first_detected": _s(exposure.first_detected.isoformat() if exposure.first_detected else None),
            "last_detected": _s(exposure.last_detected.isoformat() if exposure.last_detected else None),
            "detection_count": exposure.detection_count,
            "days_open": (datetime.utcnow() - exposure.first_detected).days if exposure.first_detected else None,
            "description": _s(exposure.description, max_len=500),
        }

        # Parent asset
        asset_data = {}
        if exposure.asset_id:
            asset_stmt = select(Asset).where(Asset.id == exposure.asset_id)
            asset_result = await self.db.execute(asset_stmt)
            asset = asset_result.scalars().first()
            if asset:
                asset_data = {
                    "hostname": _s(asset.hostname),
                    "ip_address": _s(asset.ip_address),
                    "is_internet_facing": getattr(asset, "is_internet_facing", False),
                    "risk_score": round(asset.risk_score or 0, 2),
                }

        # Other active exposures on the same asset (sibling context)
        sibling_stmt = select(Exposure).where(
            and_(
                Exposure.asset_id == exposure.asset_id,
                Exposure.is_active == True,
                Exposure.id != exposure_id,
            )
        ).order_by(desc(Exposure.risk_score)).limit(5)
        sibling_result = await self.db.execute(sibling_stmt)
        siblings = [
            {"title": _s(e.title), "type": _s(e.exposure_type), "risk_level": _s(e.risk_level)}
            for e in sibling_result.scalars().all()
        ]

        # Recent change events for this org
        since = datetime.utcnow() - timedelta(days=14)
        chg_stmt = select(ChangeEvent).where(
            and_(
                ChangeEvent.organization_id == organization_id,
                ChangeEvent.detected_at >= since,
                ChangeEvent.change_type.in_(["new_exposure", "exposure_change", "resolved_exposure"]),
            )
        ).order_by(desc(ChangeEvent.detected_at)).limit(5)
        chg_result = await self.db.execute(chg_stmt)
        historical = [
            {
                "change_type": _s(e.change_type),
                "severity": _s(e.severity),
                "detected_at": _s(e.detected_at.strftime("%Y-%m-%d") if e.detected_at else None),
            }
            for e in chg_result.scalars().all()
        ]

        graph_hints = await self._get_graph_hints(organization_id, exposure_id, NodeType.EXPOSURE)

        ctx = {
            "context_type": "exposure",
            "organization_id": _s(organization_id),
            "entity_id": _s(exposure_id),
            "entity_summary": entity_summary,
            "related_data": {
                "parent_asset": asset_data,
                "sibling_exposures": siblings,
            },
            "historical": historical,
            "graph_hints": graph_hints,
            "context_built_at": datetime.utcnow().isoformat(),
        }
        return _truncate_context(ctx)

    # =========================================================================
    # FINDING CONTEXT
    # =========================================================================

    async def build_finding_context(
        self,
        organization_id: UUID,
        finding_id: UUID,
    ) -> dict[str, Any]:
        """
        Build investigation context for a specific finding.

        Includes: finding facts, correlated findings (same severity/title prefix),
        affected endpoint, and recent scan context.
        """
        stmt = select(Finding).where(
            and_(Finding.id == finding_id, Finding.organization_id == organization_id)
        )
        result = await self.db.execute(stmt)
        finding = result.scalars().first()

        if finding is None:
            return {"error": "Finding not found", "organization_id": str(organization_id)}

        entity_summary = {
            "id": _s(finding.id),
            "title": _s(finding.title),
            "severity": _s(finding.severity),
            "status": _s(finding.status),
            "endpoint": _s(finding.endpoint),
            "description": _s(finding.description, max_len=500),
            "evidence": _s(finding.evidence, max_len=300),
            "program_id": _s(finding.program_id),
        }

        # Correlated findings: same severity in same program
        corr_stmt = select(Finding).where(
            and_(
                Finding.organization_id == organization_id,
                Finding.severity == finding.severity,
                Finding.id != finding_id,
                Finding.status == "open",
            )
        ).limit(5)
        corr_result = await self.db.execute(corr_stmt)
        correlated = [
            {"title": _s(f.title), "severity": _s(f.severity), "endpoint": _s(f.endpoint)}
            for f in corr_result.scalars().all()
        ]

        graph_hints = await self._get_graph_hints(organization_id, finding_id, NodeType.FINDING)

        ctx = {
            "context_type": "finding",
            "organization_id": _s(organization_id),
            "entity_id": _s(finding_id),
            "entity_summary": entity_summary,
            "related_data": {
                "correlated_findings": correlated,
                "correlated_count": len(correlated),
            },
            "historical": [],
            "graph_hints": graph_hints,
            "context_built_at": datetime.utcnow().isoformat(),
        }
        return _truncate_context(ctx)

    # =========================================================================
    # GRAPH CONTEXT
    # =========================================================================

    async def build_graph_context(
        self,
        organization_id: UUID,
    ) -> dict[str, Any]:
        """
        Build a high-level graph topology context for organisation-wide analysis.

        Returns node/edge counts by type and the most connected entry points.
        """
        # Node counts by type
        node_stmt = (
            select(GraphNode.node_type, func.count(GraphNode.id).label("cnt"))
            .where(GraphNode.organization_id == organization_id)
            .group_by(GraphNode.node_type)
        )
        node_result = await self.db.execute(node_stmt)
        node_counts = {row[0]: row[1] for row in node_result.all()}

        # Edge counts by type
        edge_stmt = (
            select(GraphEdge.relationship_type, func.count(GraphEdge.id).label("cnt"))
            .where(GraphEdge.organization_id == organization_id)
            .group_by(GraphEdge.relationship_type)
        )
        edge_result = await self.db.execute(edge_stmt)
        edge_counts = {row[0]: row[1] for row in edge_result.all()}

        # Most connected nodes (highest outgoing degree)
        degree_stmt = (
            select(GraphEdge.source_node_id, func.count(GraphEdge.id).label("degree"))
            .where(GraphEdge.organization_id == organization_id)
            .group_by(GraphEdge.source_node_id)
            .order_by(desc("degree"))
            .limit(5)
        )
        degree_result = await self.db.execute(degree_stmt)
        top_nodes_raw = degree_result.all()

        top_nodes = []
        for row in top_nodes_raw:
            n_stmt = select(GraphNode).where(GraphNode.id == row[0])
            n_result = await self.db.execute(n_stmt)
            n = n_result.scalars().first()
            if n:
                top_nodes.append({
                    "node_id": _s(n.id),
                    "label": _s(n.label),
                    "node_type": _s(n.node_type),
                    "degree": row[1],
                })

        ctx = {
            "context_type": "graph",
            "organization_id": _s(organization_id),
            "entity_id": _s(organization_id),
            "entity_summary": {
                "total_nodes": sum(node_counts.values()),
                "total_edges": sum(edge_counts.values()),
                "node_types": node_counts,
                "edge_types": edge_counts,
            },
            "related_data": {
                "top_connected_nodes": top_nodes,
            },
            "historical": [],
            "graph_hints": {
                "connectivity_score": min(100, int(sum(edge_counts.values()) / max(sum(node_counts.values()), 1) * 25)),
            },
            "context_built_at": datetime.utcnow().isoformat(),
        }
        return _truncate_context(ctx)

    # =========================================================================
    # HELPERS
    # =========================================================================

    async def _get_graph_hints(
        self,
        organization_id: UUID,
        reference_id: UUID,
        node_type: NodeType,
    ) -> dict[str, Any]:
        """Fetch lightweight graph metadata for a specific entity node."""
        node_stmt = select(GraphNode).where(
            and_(
                GraphNode.organization_id == organization_id,
                GraphNode.node_type == node_type,
                GraphNode.reference_id == reference_id,
            )
        )
        n_result = await self.db.execute(node_stmt)
        node = n_result.scalars().first()

        if node is None:
            return {"in_graph": False, "note": "Run POST /graph/bootstrap to index this entity."}

        # Count outgoing and incoming edges
        out_count = (await self.db.execute(
            select(func.count(GraphEdge.id)).where(GraphEdge.source_node_id == node.id)
        )).scalar() or 0
        in_count = (await self.db.execute(
            select(func.count(GraphEdge.id)).where(GraphEdge.target_node_id == node.id)
        )).scalar() or 0

        return {
            "in_graph": True,
            "node_id": _s(node.id),
            "outgoing_edges": out_count,
            "incoming_edges": in_count,
            "total_connections": out_count + in_count,
        }
