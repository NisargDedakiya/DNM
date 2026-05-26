"""
Attack reasoning orchestration service.
"""
from __future__ import annotations

import logging
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.services.ai_service import ai_service
from backend.attack.attack_path_engine import build_attack_path, correlate_attack_chain, prioritize_exploitable_paths
from backend.attack.lateral_movement import correlate_internal_assets, identify_pivot_paths, simulate_lateral_movement
from backend.attack.trust_boundary import analyze_trust_boundary, correlate_boundary_exposure, identify_trust_violations
from backend.blast.blast_radius import calculate_blast_radius, prioritize_high_impact_paths, analyze_asset_impact
from backend.blast.impact_analysis import analyze_business_impact, identify_chain_amplification, propagate_severity
from backend.models.asset import Asset
from backend.models.graph_node import NodeType
from backend.models.graph_edge import RelationshipType
from backend.models.attack_path import AttackPath
from backend.models.blast_radius_event import BlastRadiusEvent
from backend.models.privilege_chain import PrivilegeChain
from backend.privilege.auth_inheritance import analyze_auth_inheritance
from backend.privilege.privilege_propagation import analyze_privilege_chain, identify_permission_propagation, simulate_privilege_escalation
from backend.services.graph_service import GraphService

logger = logging.getLogger(__name__)


class AttackService:
    """Coordinates attack-path reasoning and blast-radius analysis."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.graph_service = GraphService(db)

    async def _load_assets(self, organization_id: UUID, limit: int = 20) -> list[Asset]:
        result = await self.db.execute(
            select(Asset).where(Asset.organization_id == organization_id).order_by(Asset.risk_score.desc()).limit(limit)
        )
        return list(result.scalars().all())

    async def generate_attack_analysis(self, organization_id: UUID, source_asset_id: UUID | None = None) -> dict[str, Any]:
        assets = await self._load_assets(organization_id)
        if not assets:
            return {"organization_id": str(organization_id), "paths": [], "blast_radius": {"affected_assets": []}, "summary": "No assets available for attack reasoning."}

        source_asset = next((asset for asset in assets if asset.id == source_asset_id), assets[0]) if source_asset_id else assets[0]
        target_assets = assets[1:6] if len(assets) > 1 else assets

        paths: list[dict[str, Any]] = []
        for target_asset in target_assets:
            hops = [
                {"step": "initial_access", "weight": 1.2, "node_type": "exposure"},
                {"step": "privilege_shift", "weight": 0.9, "node_type": "auth"},
                {"step": "lateral_move", "weight": 1.1, "node_type": "asset"},
            ]
            path = build_attack_path(
                {"id": str(source_asset.id), "hostname": source_asset.hostname, "exploitability_score": float(source_asset.risk_score or 0.0) / 2.0},
                {"id": str(target_asset.id), "hostname": target_asset.hostname, "exposure_score": float(target_asset.risk_score or 0.0) / 3.0},
                hops,
            )
            paths.append(path)

        correlated = prioritize_exploitable_paths(correlate_attack_chain(paths))
        blast_radius = calculate_blast_radius(correlated, [{"id": str(asset.id), "hostname": asset.hostname, "criticality": "high" if float(asset.risk_score or 0.0) >= 7 else "medium"} for asset in assets])

        lateral = simulate_lateral_movement(
            {
                "asset": {"id": str(source_asset.id), "hostname": source_asset.hostname},
                "initial_access_score": float(source_asset.risk_score or 0.0) / 2.0,
                "credential_reuse_score": 1.0,
                "internal_nodes": [{"asset_id": str(asset.id), "hostname": asset.hostname, "exposure_score": float(asset.risk_score or 0.0) / 10.0, "trust_score": 0.4} for asset in assets],
            }
        )
        trust = correlate_boundary_exposure(
            [
                {"source": source_asset.hostname, "target": target.hostname, "trust_score": 0.7 if float(target.risk_score or 0.0) >= 6 else 0.4, "auth_flow": "jwt_delegation", "violation_type": "wide_trust"}
                for target in target_assets
            ]
        )
        privilege = analyze_privilege_chain(
            [
                {"role": "viewer", "target_role": "analyst", "permission": "view_assets"},
                {"role": "analyst", "target_role": "admin", "permission": "manage_findings"},
            ]
        )
        auth_inheritance = analyze_auth_inheritance(
            [
                {"source": source_asset.hostname, "target": target.hostname, "token_type": "jwt", "delegation": True, "inheritance": True, "auth_flow": "oauth_session"}
                for target in target_assets[:3]
            ]
        )

        amplified = identify_chain_amplification(propagate_severity(correlated))
        business = analyze_business_impact({"affected_assets": blast_radius["affected_assets"], "impact_score": blast_radius["impact_score"]})

        ai_verdict = "Pending AI analysis"
        try:
            ai_verdict = await ai_service.analyze_finding(
                {
                    "title": f"Attack path analysis for {source_asset.hostname}",
                    "target": source_asset.hostname,
                    "severity": blast_radius["severity"],
                    "prompt": "Summarize exploitability propagation, blast radius, privilege escalation, and lateral movement.",
                }
            )
        except Exception as exc:  # pragma: no cover
            logger.warning("AI reasoning unavailable for attack analysis: %s", exc)

        await self._sync_attack_graph(organization_id, source_asset, correlated)
        await self._persist_reasoning(
            organization_id=organization_id,
            source_asset=source_asset,
            correlated_paths=correlated,
            blast_radius=blast_radius,
            privilege=privilege,
        )

        return {
            "organization_id": str(organization_id),
            "source_asset": {"id": str(source_asset.id), "hostname": source_asset.hostname},
            "paths": correlated,
            "blast_radius": blast_radius,
            "lateral_movement": lateral,
            "trust_boundary": trust,
            "privilege_chain": privilege,
            "auth_inheritance": auth_inheritance,
            "business_impact": business,
            "amplification": amplified,
            "ai_verdict": ai_verdict,
            "summary": f"Generated {len(correlated)} correlated attack paths.",
        }

    async def _persist_reasoning(self, organization_id: UUID, source_asset: Asset, correlated_paths: list[dict[str, Any]], blast_radius: dict[str, Any], privilege: dict[str, Any]) -> None:
        try:
            for path in correlated_paths:
                self.db.add(
                    AttackPath(
                        organization_id=organization_id,
                        source_asset=source_asset.hostname,
                        target_asset=str(path.get("target_asset", {}).get("hostname") or "unknown"),
                        severity=str(path.get("severity") or "low"),
                        exploitability_score=float(path.get("exploitability_score") or 0.0),
                    )
                )
            self.db.add(
                BlastRadiusEvent(
                    organization_id=organization_id,
                    affected_assets=blast_radius.get("affected_assets", []),
                    impact_score=float(blast_radius.get("impact_score") or 0.0),
                    summary=str(blast_radius.get("summary") or "Blast radius calculated."),
                )
            )
            self.db.add(
                PrivilegeChain(
                    organization_id=organization_id,
                    source_identity=source_asset.hostname,
                    escalated_privilege=str(privilege.get("severity") or "medium"),
                    severity=str(privilege.get("severity") or "medium"),
                )
            )
            await self.db.commit()
        except Exception as exc:  # pragma: no cover
            logger.warning("Persisting attack reasoning failed: %s", exc)
            await self.db.rollback()

    async def _sync_attack_graph(self, organization_id: UUID, source_asset: Asset, correlated_paths: list[dict[str, Any]]) -> None:
        """Create lightweight graph correlations for attack paths without exposing raw reasoning payloads."""
        try:
            source_node = await self.graph_service.create_node(
                organization_id=organization_id,
                node_type=NodeType.ASSET,
                reference_id=source_asset.id,
                label=source_asset.hostname,
                node_metadata={"risk_score": float(source_asset.risk_score or 0.0)},
            )
            for path in correlated_paths:
                target_payload = path.get("target_asset") or {}
                target_id = target_payload.get("id")
                if not target_id:
                    continue
                from uuid import UUID as _UUID

                target_node = await self.graph_service.create_node(
                    organization_id=organization_id,
                    node_type=NodeType.ASSET,
                    reference_id=_UUID(str(target_id)),
                    label=str(target_payload.get("hostname") or "unknown"),
                    node_metadata={
                        "severity": str(path.get("severity") or "low"),
                        "exploitability_score": float(path.get("exploitability_score") or 0.0),
                    },
                )
                await self.graph_service.create_edge(
                    organization_id=organization_id,
                    source_node_id=source_node.id,
                    target_node_id=target_node.id,
                    relationship_type=RelationshipType.RELATED_TO,
                    confidence_score=min(1.0, float(path.get("exploitability_score") or 0.0) / 10.0),
                    notes="Attack-path correlation",
                )
        except Exception as exc:  # pragma: no cover
            logger.warning("Graph sync skipped during attack reasoning: %s", exc)

    async def calculate_exploitability(self, organization_id: UUID, asset_id: UUID | None = None) -> dict[str, Any]:
        analysis = await self.generate_attack_analysis(organization_id, source_asset_id=asset_id)
        exploitability = max((float(path.get("exploitability_score") or 0.0) for path in analysis.get("paths", [])), default=0.0)
        return {
            "organization_id": analysis["organization_id"],
            "asset_id": str(asset_id) if asset_id else None,
            "exploitability_score": round(exploitability, 2),
            "severity": analysis.get("blast_radius", {}).get("severity", "low"),
            "summary": analysis.get("summary"),
        }

    async def generate_attack_summary(self, organization_id: UUID) -> dict[str, Any]:
        analysis = await self.generate_attack_analysis(organization_id)
        return {
            "organization_id": analysis["organization_id"],
            "summary": analysis["summary"],
            "paths": analysis["paths"][:5],
            "blast_radius": analysis["blast_radius"],
            "lateral_movement": analysis["lateral_movement"],
            "privilege_chain": analysis["privilege_chain"],
            "auth_inheritance": analysis["auth_inheritance"],
        }