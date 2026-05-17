"""
Investigation Service: orchestrates full investigation workflows.

Coordinates ContextService, IntelligenceGraphService, and
InvestigationAssistant to produce complete, auditable investigation packages.
Each investigation is assembled from live DB data and AI analysis, then
returned as a structured payload for API consumption.

Advisory contract
-----------------
All investigation outputs carry:
- ``requires_human_review: True``
- ``advisory_note`` with explicit disclaimer
- No shell commands, network actions, or autonomous execution steps

Workspace isolation
-------------------
All DB queries MUST be scoped to organization_id.
No investigation data is persisted without user intent (reports are
only written if the caller explicitly requests it via the reporting service).
"""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from backend.services.context_service import ContextService
from backend.services.graph_service import GraphService
from backend.services.intelligence_graph_service import IntelligenceGraphService
from backend.ai.investigation_assistant import InvestigationAssistant
from backend.ai.copilot_engine import CopilotEngine

logger = logging.getLogger(__name__)

_ADVISORY = (
    "⚠️ All AI analysis is advisory only. "
    "No action should be taken without explicit human analyst review and approval."
)


class InvestigationService:
    """
    Orchestrates end-to-end investigation workflows.

    Combines context assembly, graph intelligence, and AI analysis into
    a unified investigation package for API delivery.
    """

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self._ctx_svc = ContextService(db)
        self._graph_svc = GraphService(db)
        self._intel_graph = IntelligenceGraphService(db)
        self._assistant = InvestigationAssistant(db)
        self._engine = CopilotEngine()

    # =========================================================================
    # START INVESTIGATION
    # =========================================================================

    async def start_investigation(
        self,
        organization_id: UUID,
        investigation_type: str,
        entity_id: UUID,
        analyst_note: str | None = None,
    ) -> dict[str, Any]:
        """
        Start a full AI-assisted investigation for an entity.

        Supported types: "asset", "exposure", "finding"

        Parameters
        ----------
        organization_id :
            Workspace scope (enforced on all sub-queries).
        investigation_type :
            "asset", "exposure", or "finding".
        entity_id :
            UUID of the entity to investigate.
        analyst_note :
            Optional analyst context to include in the investigation.

        Returns
        -------
        dict with:
            investigation_id    – timestamp-based unique ID for this session
            investigation_type  – echoed back
            entity_id           – echoed back
            context             – assembled investigation context
            ai_analysis         – AI explanation/summary (advisory)
            investigation_steps – ordered analyst checklist (advisory)
            graph_intelligence  – graph neighbourhood and risk propagation
            historical_context  – 14-day change event summary
            analyst_note        – sanitised analyst note (if provided)
            advisory_note       – mandatory advisory disclaimer
            requires_human_review – always True
            generated_at        – ISO timestamp
        """
        import re
        safe_note = re.sub(r"[\x00-\x1f\x7f]", " ", str(analyst_note or ""))[:400]

        if investigation_type == "asset":
            return await self._investigate_asset(organization_id, entity_id, safe_note)
        elif investigation_type == "exposure":
            return await self._investigate_exposure(organization_id, entity_id, safe_note)
        elif investigation_type == "finding":
            return await self._investigate_finding(organization_id, entity_id, safe_note)
        else:
            return {
                "error": f"Unknown investigation_type '{investigation_type}'. Valid: asset, exposure, finding.",
                "advisory_note": _ADVISORY,
                "requires_human_review": True,
            }

    # =========================================================================
    # CORRELATE INVESTIGATION CONTEXT
    # =========================================================================

    async def correlate_investigation_context(
        self,
        organization_id: UUID,
        primary_entity_id: UUID,
        primary_type: str,
    ) -> dict[str, Any]:
        """
        Enrich an investigation with correlated graph intelligence.

        Runs risk propagation from the primary entity's graph node and
        identifies related high-risk clusters.

        Returns
        -------
        dict with:
            risk_propagation    – risk spread from primary entity
            related_clusters    – overlapping high-risk clusters
            graph_neighbourhood – one-hop neighbours
        """
        from backend.models.graph_node import NodeType

        type_map = {
            "asset": NodeType.ASSET,
            "exposure": NodeType.EXPOSURE,
            "finding": NodeType.FINDING,
        }
        node_type = type_map.get(primary_type)

        # Find the graph node for this entity
        node = None
        if node_type:
            node = await self._graph_svc.get_node(
                organization_id=organization_id,
                node_type=node_type,
                reference_id=primary_entity_id,
            )

        if node is None:
            return {
                "note": "Entity not in graph — run POST /graph/bootstrap to index it.",
                "risk_propagation": {},
                "related_clusters": {},
                "graph_neighbourhood": {},
            }

        # Risk propagation from this node
        propagation = await self._intel_graph.calculate_risk_propagation(
            organization_id=organization_id,
            start_node_id=node.id,
            max_depth=2,
        )

        # Graph neighbourhood
        neighbourhood = await self._graph_svc.get_connected_nodes(
            organization_id=organization_id,
            node_id=node.id,
            direction="both",
            limit=20,
        )

        # High-risk clusters
        clusters = await self._intel_graph.identify_high_risk_clusters(
            organization_id=organization_id,
            risk_threshold=0.5,
            min_cluster_size=2,
        )

        return {
            "primary_node": {
                "id": str(node.id),
                "label": node.label,
                "node_type": str(node.node_type),
            },
            "risk_propagation": {
                "total_affected": propagation.get("total_affected", 0),
                "max_propagated_risk": propagation.get("max_propagated_risk", 0),
                "affected_nodes": list(propagation.get("propagated_risks", {}).values())[:5],
            },
            "graph_neighbourhood": {
                "edge_count": len(neighbourhood.get("edges", [])),
                "neighbour_count": len(neighbourhood.get("nodes", [])),
                "neighbours": neighbourhood.get("nodes", [])[:10],
            },
            "related_clusters": {
                "cluster_count": clusters.get("total_clusters", 0),
                "top_clusters": clusters.get("clusters", [])[:3],
            },
        }

    # =========================================================================
    # GENERATE INVESTIGATION REPORT
    # =========================================================================

    async def generate_investigation_report(
        self,
        organization_id: UUID,
        investigation_data: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Generate a final investigation summary from a completed investigation package.

        Calls InvestigationAssistant.generate_investigation_summary() to
        produce a structured, shareable investigation report.

        Returns
        -------
        dict with: investigation_title, executive_summary, key_findings,
                   risk_verdict, recommended_next_actions, advisory_note.
        """
        context = investigation_data.get("context", {})
        ai_analysis = investigation_data.get("ai_analysis") or investigation_data.get("ai_summary") or {}

        summary = await self._assistant.generate_investigation_summary(
            context=context,
            findings_so_far=ai_analysis,
        )

        summary["organization_id"] = str(organization_id)
        summary["investigation_type"] = investigation_data.get("investigation_type", "unknown")
        summary["entity_id"] = investigation_data.get("entity_id", "unknown")
        return summary

    # =========================================================================
    # INTERNAL INVESTIGATION HELPERS
    # =========================================================================

    async def _investigate_asset(
        self, organization_id: UUID, asset_id: UUID, analyst_note: str
    ) -> dict[str, Any]:
        """Full asset investigation package."""
        inv_id = f"inv-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}-{str(asset_id)[:8]}"

        # Core investigation from assistant
        core = await self._assistant.investigate_asset(organization_id, asset_id)

        # Graph correlation
        graph_intel = await self.correlate_investigation_context(
            organization_id, asset_id, "asset"
        )

        # Historical context
        historical = await self._ctx_svc.retrieve_historical_context(
            organization_id, days=14, limit=20
        )

        return {
            "investigation_id": inv_id,
            "investigation_type": "asset",
            "entity_id": str(asset_id),
            "organization_id": str(organization_id),
            "context": core.get("context", {}),
            "ai_analysis": core.get("ai_summary", {}),
            "investigation_steps": core.get("investigation_steps", {}),
            "graph_intelligence": graph_intel,
            "historical_context": historical,
            "analyst_note": analyst_note,
            "advisory_note": _ADVISORY,
            "requires_human_review": True,
            "generated_at": datetime.utcnow().isoformat(),
        }

    async def _investigate_exposure(
        self, organization_id: UUID, exposure_id: UUID, analyst_note: str
    ) -> dict[str, Any]:
        """Full exposure investigation package."""
        inv_id = f"inv-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}-{str(exposure_id)[:8]}"

        core = await self._assistant.investigate_exposure(organization_id, exposure_id)
        graph_intel = await self.correlate_investigation_context(
            organization_id, exposure_id, "exposure"
        )
        historical = await self._ctx_svc.retrieve_historical_context(
            organization_id, days=14, limit=20
        )

        return {
            "investigation_id": inv_id,
            "investigation_type": "exposure",
            "entity_id": str(exposure_id),
            "organization_id": str(organization_id),
            "context": core.get("context", {}),
            "ai_analysis": core.get("ai_explanation", {}),
            "investigation_steps": core.get("investigation_steps", {}),
            "graph_intelligence": graph_intel,
            "historical_context": historical,
            "analyst_note": analyst_note,
            "advisory_note": _ADVISORY,
            "requires_human_review": True,
            "generated_at": datetime.utcnow().isoformat(),
        }

    async def _investigate_finding(
        self, organization_id: UUID, finding_id: UUID, analyst_note: str
    ) -> dict[str, Any]:
        """Finding investigation package (context + AI chat)."""
        inv_id = f"inv-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}-{str(finding_id)[:8]}"

        context = await self._ctx_svc.get_finding_context(organization_id, finding_id)
        ai_analysis = await self._engine.generate_copilot_response(
            user_message="Explain this finding and its security impact.",
            context=context,
        )
        steps = await self._assistant.recommend_investigation_steps(
            context_type="finding",
            entity_summary=context.get("entity_summary", {}),
            risk_level=context.get("entity_summary", {}).get("severity", "unknown"),
            exposure_count=context.get("related_data", {}).get("correlated_count", 0),
            graph_connections=context.get("graph_hints", {}).get("total_connections", 0),
        )
        graph_intel = await self.correlate_investigation_context(
            organization_id, finding_id, "finding"
        )

        return {
            "investigation_id": inv_id,
            "investigation_type": "finding",
            "entity_id": str(finding_id),
            "organization_id": str(organization_id),
            "context": context,
            "ai_analysis": ai_analysis,
            "investigation_steps": steps,
            "graph_intelligence": graph_intel,
            "historical_context": {},
            "analyst_note": analyst_note,
            "advisory_note": _ADVISORY,
            "requires_human_review": True,
            "generated_at": datetime.utcnow().isoformat(),
        }
