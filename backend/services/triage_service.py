"""
Triage service orchestrating AI triage with contextual intelligence.
"""
from __future__ import annotations

import json
from typing import Any
from uuid import UUID

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.ai.triage import (
    analyze_exploitability,
    classify_finding,
    generate_confidence_score,
    summarize_risk,
)
from backend.models.exposure import Exposure
from backend.models.finding import Finding
from backend.models.graph_edge import GraphEdge
from backend.models.graph_node import GraphNode, NodeType
from backend.models.technology import Technology
from backend.models.triage_result import TriageResult
from backend.services.confidence_service import ConfidenceService
from backend.services.exploitability_service import ExploitabilityService


class TriageService:
    """Runs safe AI triage and persists historical triage snapshots."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.confidence_service = ConfidenceService()
        self.exploitability_service = ExploitabilityService()

    async def enrich_finding_context(self, finding: Finding) -> dict[str, Any]:
        """Assemble context from finding, exposure, technology, and graph layers."""
        tech_result = await self.db.execute(
            select(Technology.name)
            .join(Technology.asset)
            .where(Technology.asset_id.is_not(None))
            .limit(20)
        )
        fingerprints = [row[0] for row in tech_result.all()]

        exposure_count_result = await self.db.execute(
            select(func.count(Exposure.id)).where(
                and_(
                    Exposure.organization_id == finding.organization_id,
                    Exposure.finding_id == finding.id,
                    Exposure.is_active == True,
                )
            )
        )
        related_exposure_count = int(exposure_count_result.scalar() or 0)

        duplicate_count_result = await self.db.execute(
            select(func.count(Finding.id)).where(
                and_(
                    Finding.organization_id == finding.organization_id,
                    Finding.title == finding.title,
                    Finding.id != finding.id,
                )
            )
        )
        duplicate_count = int(duplicate_count_result.scalar() or 0)

        node_result = await self.db.execute(
            select(GraphNode.id).where(
                and_(
                    GraphNode.organization_id == finding.organization_id,
                    GraphNode.node_type == NodeType.FINDING,
                    GraphNode.reference_id == finding.id,
                )
            )
        )
        node_id = node_result.scalar()

        graph_neighbor_count = 0
        if node_id:
            edge_result = await self.db.execute(
                select(func.count(GraphEdge.id)).where(
                    and_(
                        GraphEdge.organization_id == finding.organization_id,
                        (GraphEdge.source_node_id == node_id) | (GraphEdge.target_node_id == node_id),
                    )
                )
            )
            graph_neighbor_count = int(edge_result.scalar() or 0)

        endpoint = str(finding.endpoint or "")

        return {
            "finding_id": str(finding.id),
            "organization_id": str(finding.organization_id) if finding.organization_id else None,
            "title": finding.title,
            "scanner_severity": str(getattr(finding.severity, "value", finding.severity)).lower(),
            "description": finding.description,
            "endpoint": endpoint,
            "evidence": finding.evidence or "",
            "fingerprints": fingerprints,
            "related_exposure_count": related_exposure_count,
            "duplicate_count": duplicate_count,
            "graph_neighbor_count": graph_neighbor_count,
            "internet_facing": endpoint.startswith("http"),
            "auth_involvement": any(k in endpoint.lower() for k in ["auth", "login", "token", "oauth", "sso"]),
            "asset_hostname": endpoint.split("/")[2] if endpoint.startswith("http") and "/" in endpoint else endpoint,
        }

    async def correlate_finding_intelligence(self, context: dict[str, Any]) -> dict[str, Any]:
        """Generate cross-signal intelligence correlation summary."""
        high_signal_flags: list[str] = []
        endpoint = str(context.get("endpoint") or "").lower()

        if any(k in endpoint for k in ["admin", "auth", "graphql", "upload", "api"]):
            high_signal_flags.append("high_value_endpoint_class")

        if int(context.get("related_exposure_count") or 0) > 0:
            high_signal_flags.append("linked_exposure_context")

        if int(context.get("graph_neighbor_count") or 0) >= 3:
            high_signal_flags.append("graph_cluster_density")

        if any(str(fp).lower() in {"jenkins", "gitlab", "kubernetes", "wordpress", "graphql"} for fp in context.get("fingerprints", [])):
            high_signal_flags.append("risky_technology_signal")

        return {
            "high_signal_flags": high_signal_flags,
            "high_signal_score": min(len(high_signal_flags) / 4.0, 1.0),
        }

    async def run_ai_triage(self, finding_id: UUID, organization_id: UUID) -> dict[str, Any]:
        """Run AI triage and persist immutable triage result snapshot."""
        finding_result = await self.db.execute(
            select(Finding).where(
                and_(
                    Finding.id == finding_id,
                    Finding.organization_id == organization_id,
                )
            )
        )
        finding = finding_result.scalars().first()
        if not finding:
            raise ValueError("Finding not found in organization scope")

        context = await self.enrich_finding_context(finding)
        correlation = await self.correlate_finding_intelligence(context)
        context["signals"] = correlation

        deterministic_exploitability = self.exploitability_service.evaluate_exploitability(context)
        deterministic_confidence = self.confidence_service.calculate_confidence(context)

        context["exploitability_score"] = deterministic_exploitability["exploitability_score"]
        context["confidence_score"] = deterministic_confidence["confidence_score"]
        context["evidence_quality"] = "high" if context.get("evidence") else "low"
        context["exposure_context"] = deterministic_exploitability["attack_surface"]
        context["graph_context"] = {"neighbor_count": context.get("graph_neighbor_count", 0)}

        ai_exploitability = await analyze_exploitability(context, organization_id=str(organization_id))
        ai_confidence = await generate_confidence_score(context, organization_id=str(organization_id))

        # Blend deterministic and AI advisory scores for resilient scoring.
        exploitability_score = (
            (deterministic_exploitability["exploitability_score"] * 0.6)
            + (float(ai_exploitability.get("exploitability_score", 0.0)) * 0.4)
        )
        confidence_score = (
            (deterministic_confidence["confidence_score"] * 0.65)
            + (float(ai_confidence.get("confidence_score", 0.0)) * 0.35)
        )

        context["exploitability_score"] = max(0.0, min(exploitability_score, 1.0))
        context["confidence_score"] = max(0.0, min(confidence_score, 1.0))

        classification = await classify_finding(context, organization_id=str(organization_id))
        summary = await summarize_risk(
            {
                **context,
                "priority": classification["priority"],
            },
            organization_id=str(organization_id),
        )

        reasoning_payload = {
            "classification": classification,
            "ai_exploitability": ai_exploitability,
            "ai_confidence": ai_confidence,
            "deterministic_exploitability": deterministic_exploitability,
            "deterministic_confidence": deterministic_confidence,
            "correlation": correlation,
            "advisory_only": True,
            "human_verification_required": True,
        }

        triage_result = TriageResult(
            organization_id=organization_id,
            finding_id=finding.id,
            severity=classification["priority"],
            confidence_score=context["confidence_score"],
            exploitability_score=context["exploitability_score"],
            ai_summary=summary["summary"],
            reasoning=json.dumps(reasoning_payload, default=str),
        )
        self.db.add(triage_result)
        await self.db.commit()
        await self.db.refresh(triage_result)

        return {
            "triage_result_id": str(triage_result.id),
            "finding_id": str(finding.id),
            "severity": triage_result.severity,
            "confidence_score": triage_result.confidence_score,
            "exploitability_score": triage_result.exploitability_score,
            "ai_summary": triage_result.ai_summary,
            "reasoning": reasoning_payload,
            "created_at": str(triage_result.created_at),
            "advisory_only": True,
            "human_verification_required": True,
        }
