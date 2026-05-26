"""
Strategy orchestration service for hunt planning and campaign intelligence.
"""
from __future__ import annotations

import hashlib
import logging
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.adaptive.adaptive_recon import adapt_recon_flow, evolve_scan_strategy, prioritize_followup_scans
from backend.adaptive.strategy_memory import StrategyMemoryStore
from backend.campaigns.campaign_engine import CampaignEngine
from backend.campaigns.recon_orchestrator import correlate_recon_results
from backend.core.permissions import Permission, RBACService
from backend.models.asset import Asset
from backend.models.attack_path import AttackPath
from backend.models.exposure import Exposure
from backend.models.finding import Finding
from backend.models.hunt_strategy import HuntStrategy
from backend.models.monitoring_rule import MonitoringRule
from backend.models.recon_campaign import ReconCampaign
from backend.models.strategy_memory import StrategyMemory
from backend.models.threat_intel import ThreatIntel
from backend.services.ai_service import ai_service
from backend.strategy.hunt_planner import adapt_hunt_strategy, generate_hunt_plan, prioritize_recon_sequence

logger = logging.getLogger(__name__)


class StrategyService:
    """Orchestrates strategy planning, campaign staging, and campaign memory."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.memory_store = StrategyMemoryStore(db)
        self.campaign_engine = CampaignEngine(db)

    async def _require_access(self, user_id: UUID, organization_id: UUID) -> None:
        await RBACService(self.db).validate_workspace_access(user_id, organization_id)
        await RBACService(self.db).check_permission(user_id, organization_id, Permission.RUN_SCANS)

    async def _load_targets(self, organization_id: UUID, limit: int = 20) -> list[dict[str, Any]]:
        result = await self.db.execute(
            select(Asset)
            .where(Asset.organization_id == organization_id)
            .order_by(Asset.risk_score.desc(), Asset.last_seen.desc())
            .limit(limit),
        )
        assets = result.scalars().all()
        targets: list[dict[str, Any]] = []

        for asset in assets:
            exposure_count = await self.db.scalar(
                select(func.count(Exposure.id)).where(Exposure.asset_id == asset.id, Exposure.is_active == True),
            )
            finding_count = await self.db.scalar(
                select(func.count(Finding.id)).where(Finding.organization_id == organization_id),
            )
            threat_count = await self.db.scalar(
                select(func.count(ThreatIntel.id)).where(ThreatIntel.organization_id == organization_id, ThreatIntel.asset == asset.hostname),
            )
            targets.append({
                "id": str(asset.id),
                "name": asset.hostname,
                "hostname": asset.hostname,
                "program_id": str(asset.program_id),
                "risk_score": float(asset.risk_score or 0.0),
                "business_criticality": min(10.0, float(asset.risk_score or 0.0) + 2.0),
                "exposure_score": float(exposure_count or 0),
                "threat_score": float(threat_count or 0),
                "internet_facing": True,
                "has_auth": any(token in asset.hostname.lower() for token in ["auth", "login", "sso", "oauth"]),
                "has_graphql": "graphql" in asset.hostname.lower(),
                "tags": ["admin" if "admin" in asset.hostname.lower() else "api" if "api" in asset.hostname.lower() else "host"],
                "priority_reason": "Asset is risk-ranked and correlated with workspace signals.",
                "finding_count": int(finding_count or 0),
            })
        return targets

    async def generate_strategy_summary(self, organization_id: UUID) -> dict[str, Any]:
        targets = await self._load_targets(organization_id)
        prioritized = prioritize_recon_sequence(targets, {"focus_areas": ["auth", "graphql", "admin", "cloud"]})
        strategies = await self.db.execute(
            select(HuntStrategy).where(HuntStrategy.organization_id == organization_id).order_by(HuntStrategy.created_at.desc()).limit(10),
        )
        campaigns = await self.db.execute(
            select(ReconCampaign).where(ReconCampaign.organization_id == organization_id).order_by(ReconCampaign.created_at.desc()).limit(10),
        )
        strategy_rows = strategies.scalars().all()
        campaign_rows = campaigns.scalars().all()
        memory = await self.memory_store.evolve_historical_methodologies(organization_id)

        ai_note = "Advisory strategy summary generated from org-scoped intelligence."
        try:
            ai_note = await ai_service.explain_attack_chain({
                "organization_id": str(organization_id),
                "targets": [target["name"] for target in prioritized[:5]],
                "focus_areas": ["auth", "graphql", "admin", "cloud"],
            })
        except Exception as exc:  # pragma: no cover
            logger.warning("AI summary unavailable for strategy service: %s", exc)

        return {
            "organization_id": str(organization_id),
            "hunts": [
                {
                    "id": strategy.id,
                    "strategy_type": strategy.strategy_type,
                    "target_scope": strategy.target_scope or [],
                    "priority_score": strategy.priority_score,
                    "created_at": strategy.created_at,
                }
                for strategy in strategy_rows
            ],
            "targets": prioritized[:10],
            "strategy_count": len(strategy_rows),
            "campaign_count": len(campaign_rows),
            "strategy_memory": memory,
            "ai_note": ai_note,
        }

    async def orchestrate_autonomous_hunt(self, organization_id: UUID, user_id: UUID, target_scope: list[dict[str, Any]] | None = None) -> dict[str, Any]:
        await self._require_access(user_id, organization_id)
        targets = target_scope or await self._load_targets(organization_id)
        context = {
            "strategy_type": "autonomous_hunt",
            "focus_areas": ["auth", "graphql", "admin", "cloud"],
            "monitoring_signals": ["realtime_monitoring", "attack_graph", "threat_intel"],
            "risk_signals": [target.get("priority_score", 0) for target in targets[:5]],
        }
        hunt_plan = generate_hunt_plan(str(organization_id), targets, context)
        hunt_row = HuntStrategy(
            organization_id=organization_id,
            strategy_type=hunt_plan["strategy_type"],
            target_scope=hunt_plan["target_scope"],
            priority_score=float(hunt_plan["priority_score"]),
        )
        self.db.add(hunt_row)
        await self.db.commit()
        await self.db.refresh(hunt_row)

        campaign = await self.campaign_engine.create_campaign(
            organization_id=organization_id,
            campaign_name=f"{hunt_plan['strategy_type']}-campaign",
            methodology=hunt_plan["methodology"],
        )

        staged = await self.campaign_engine.execute_campaign(organization_id, campaign.id, approved=False)
        memory = await self.memory_store.store_strategy_pattern(
            organization_id=organization_id,
            methodology_pattern={
                "hunt_plan": hunt_plan,
                "staged_campaign": staged,
                "generated_at": datetime.now(timezone.utc).isoformat(),
            },
            success_score=0.72,
        )

        adaptive = adapt_recon_flow({
            "organization_id": str(organization_id),
            "campaign_name": campaign.campaign_name,
            "critical_findings": int(sum(1 for target in targets if float(target.get("priority_score", 0)) >= 75)),
            "active_exposures": int(sum(float(target.get("exposure_score", 0)) for target in targets)),
        })

        return {
            "organization_id": str(organization_id),
            "hunt_strategy": {
                "id": hunt_row.id,
                "strategy_type": hunt_row.strategy_type,
                "target_scope": hunt_row.target_scope or [],
                "priority_score": hunt_row.priority_score,
                "created_at": hunt_row.created_at,
            },
            "campaign": staged,
            "strategy_memory_id": memory.id,
            "adaptive_recon": adaptive,
            "advisory_note": "Campaigns remain approval-gated and workspace-isolated.",
        }

    async def correlate_campaign_intelligence(self, organization_id: UUID) -> dict[str, Any]:
        targets = await self._load_targets(organization_id)
        campaigns = await self.db.execute(
            select(ReconCampaign).where(ReconCampaign.organization_id == organization_id).order_by(ReconCampaign.created_at.desc()).limit(20),
        )
        attack_paths = await self.db.execute(
            select(AttackPath).where(AttackPath.organization_id == organization_id).order_by(AttackPath.created_at.desc()).limit(20),
        )
        monitoring = await self.db.execute(
            select(MonitoringRule).where(MonitoringRule.organization_id == organization_id).order_by(MonitoringRule.created_at.desc()).limit(20),
        )

        campaign_rows = campaigns.scalars().all()
        attack_rows = attack_paths.scalars().all()
        monitoring_rows = monitoring.scalars().all()

        intelligence = correlate_recon_results([
            {"target": row.source_asset, "severity": row.severity, "score": row.exploitability_score}
            for row in attack_rows
        ])
        recommendations = prioritize_followup_scans({
            "critical_findings": int(sum(1 for target in targets if float(target.get("priority_score", 0)) >= 80)),
            "active_exposures": len(attack_rows),
        })

        return {
            "organization_id": str(organization_id),
            "targets": targets[:10],
            "campaigns": [
                {
                    "id": campaign.id,
                    "campaign_name": campaign.campaign_name,
                    "status": campaign.status,
                    "methodology": campaign.methodology or {},
                    "created_at": campaign.created_at,
                }
                for campaign in campaign_rows
            ],
            "attack_intelligence": intelligence,
            "monitoring_signals": [
                {
                    "id": rule.id,
                    "name": rule.name,
                    "frequency": rule.frequency.value if hasattr(rule.frequency, "value") else str(rule.frequency),
                    "enabled": rule.enabled,
                    "created_at": rule.created_at,
                }
                for rule in monitoring_rows
            ],
            "follow_up_recommendations": recommendations,
            "advisory_note": "All campaign intelligence is filtered to the current organization and remains advisory.",
        }
