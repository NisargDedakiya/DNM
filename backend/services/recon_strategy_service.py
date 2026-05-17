"""
Recon strategy orchestration service.

Coordinates AI planning, asset intelligence, exposure analytics,
and recommendation generation into a unified strategy layer.
All plans require human approval before execution.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.asset import Asset
from backend.models.finding import Finding
from backend.models.exposure import Exposure
from backend.ai.recon_planner import (
    generate_recon_plan,
    analyze_asset_context,
    recommend_scan_strategy,
)
from backend.ai.recommendation_engine import (
    recommend_next_actions,
    recommend_asset_focus,
    recommend_followup_scans,
)
from backend.ai.workflow_engine import build_workflow, recommend_next_stage

logger = logging.getLogger(__name__)


class ReconStrategyService:
    """
    Orchestrates AI-assisted recon strategy creation and evaluation.

    All AI outputs are advisory. Scope enforcement is preserved.
    No autonomous scan execution occurs in this service.
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_recon_strategy(
        self,
        organization_id: UUID,
        program_id: Optional[UUID] = None,
        program_name: str = "Unnamed Program",
        scope_domains: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Create a complete AI-assisted recon strategy.

        Gathers asset intelligence, exposure data, and findings history,
        then calls the AI planner to generate a structured plan.

        Args:
            organization_id: Organization context
            program_id: Optional program scope
            program_name: Human-readable program name
            scope_domains: In-scope domains

        Returns:
            dict: Full strategy with plan, workflow, and recommendations
        """
        context = await self.evaluate_recon_context(organization_id, program_id)

        plan = await generate_recon_plan(
            asset_count=context["asset_count"],
            technologies=context["technologies"],
            active_exposures=context["active_exposures"],
            risk_distribution=context["risk_distribution"],
            recent_findings=context["recent_findings"],
            scope_domains=scope_domains or context.get("domains", []),
            organization_id=organization_id,
        )

        workflow = await build_workflow(
            program_name=program_name,
            scope_domains=scope_domains or context.get("domains", []),
            asset_types=context.get("asset_types", []),
            risk_level=context.get("overall_risk_level", "medium"),
            technologies=context["technologies"],
            existing_coverage=context.get("existing_coverage", []),
            program_id=program_id,
        )

        recommendations = await self.generate_recommendations(
            organization_id=organization_id,
            program_id=program_id,
        )

        return {
            "strategy_id": f"strategy_{organization_id}_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
            "organization_id": str(organization_id),
            "program_id": str(program_id) if program_id else None,
            "created_at": datetime.utcnow().isoformat(),
            "status": "pending_human_review",
            "context_summary": context,
            "recon_plan": plan,
            "workflow": workflow,
            "recommendations": recommendations,
            "advisory_note": (
                "This strategy is AI-generated and advisory-only. "
                "All stages and actions require human review and approval."
            ),
        }

    async def evaluate_recon_context(
        self,
        organization_id: UUID,
        program_id: Optional[UUID] = None,
    ) -> Dict[str, Any]:
        """
        Evaluate current recon context by aggregating asset, exposure,
        and findings intelligence.

        Args:
            organization_id: Organization ID
            program_id: Optional program scope filter

        Returns:
            dict: Context summary for AI planner input
        """
        # Asset query — filter by program_id if given, else by organization_id
        if program_id:
            asset_query = select(Asset).where(Asset.program_id == program_id)
        else:
            asset_query = select(Asset).where(Asset.organization_id == organization_id)

        asset_result = await self.db.execute(asset_query)
        assets = asset_result.scalars().all()

        # Exposure aggregation
        exposure_query = select(Exposure).where(
            and_(
                Exposure.organization_id == organization_id,
                Exposure.is_active == True,
            )
        )
        exp_result = await self.db.execute(exposure_query)
        exposures = exp_result.scalars().all()

        # Findings in last 30 days (by organization_id; Finding has no asset_id)
        since = datetime.utcnow() - timedelta(days=30)
        findings_result = await self.db.execute(
            select(func.count(Finding.id)).where(
                and_(
                    Finding.organization_id == organization_id,
                    Finding.created_at >= since,
                )
            )
        )
        recent_findings = findings_result.scalar() or 0

        # Aggregate technology list from asset metadata (safe - no user injection)
        technologies: List[str] = []
        asset_types: List[str] = []
        domains: List[str] = []

        for asset in assets:
            hostname = getattr(asset, "hostname", "")
            if hostname:
                domains.append(hostname)
            asset_type = getattr(asset, "asset_type", None) or "web"
            if asset_type not in asset_types:
                asset_types.append(asset_type)

        # Risk distribution from exposures
        risk_distribution: Dict[str, int] = {}
        for exp in exposures:
            lvl = exp.risk_level or "unknown"
            risk_distribution[lvl] = risk_distribution.get(lvl, 0) + 1

        # Determine overall risk
        if risk_distribution.get("critical", 0) > 0:
            overall_risk = "critical"
        elif risk_distribution.get("high", 0) > 3:
            overall_risk = "high"
        elif risk_distribution.get("medium", 0) > 5:
            overall_risk = "medium"
        else:
            overall_risk = "low"

        return {
            "asset_count": len(assets),
            "technologies": technologies,
            "asset_types": asset_types,
            "domains": domains[:10],
            "active_exposures": len(exposures),
            "risk_distribution": risk_distribution,
            "overall_risk_level": overall_risk,
            "recent_findings": recent_findings,
            "existing_coverage": [],
            "evaluated_at": datetime.utcnow().isoformat(),
        }

    async def generate_recommendations(
        self,
        organization_id: UUID,
        program_id: Optional[UUID] = None,
    ) -> Dict[str, Any]:
        """
        Generate comprehensive AI recommendations for the organization.

        Args:
            organization_id: Organization ID
            program_id: Optional program scope

        Returns:
            dict: Next actions, asset focus, and follow-up scans
        """
        context = await self.evaluate_recon_context(organization_id, program_id)

        critical_exp = context["risk_distribution"].get("critical", 0)
        high_exp = context["risk_distribution"].get("high", 0)
        high_risk_assets = critical_exp + high_exp

        next_actions = await recommend_next_actions(
            active_findings=context["recent_findings"],
            critical_exposures=critical_exp,
            high_risk_assets=high_risk_assets,
            last_scan_date=None,
            unscanned_assets=max(0, context["asset_count"] - 1),
            technology_stack=context["technologies"],
            organization_id=organization_id,
        )

        asset_focus = await recommend_asset_focus(
            total_assets=context["asset_count"],
            exposure_distribution=context["risk_distribution"],
            technology_mix=context["technologies"],
            recent_activity={"recent_findings": context["recent_findings"]},
            uncovered_assets=max(0, context["asset_count"] - 1),
            organization_id=organization_id,
        )

        followup_scans = await recommend_followup_scans(
            finding_types=["misconfiguration", "outdated_technology"],
            severity_counts=context["risk_distribution"],
            affected_assets=context["domains"][:5],
            technologies=context["technologies"],
            scan_gaps=["api_endpoints", "admin_panels"],
            program_id=program_id,
        )

        return {
            "next_actions": next_actions,
            "asset_focus": asset_focus,
            "followup_scans": followup_scans,
            "generated_at": datetime.utcnow().isoformat(),
        }
