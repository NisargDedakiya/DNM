"""
Campaign engine for staged and approved offensive strategy orchestration.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from backend.models.recon_campaign import ReconCampaign
from backend.strategy.hunt_planner import adapt_hunt_strategy
from backend.campaigns.recon_orchestrator import orchestrate_recon


class CampaignEngine:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_campaign(self, organization_id: UUID, campaign_name: str, methodology: dict[str, Any]) -> ReconCampaign:
        campaign = ReconCampaign(
            organization_id=organization_id,
            campaign_name=campaign_name,
            status="pending_approval",
            methodology=methodology,
        )
        self.db.add(campaign)
        await self.db.commit()
        await self.db.refresh(campaign)
        return campaign

    async def execute_campaign(self, organization_id: UUID, campaign_id: UUID, approved: bool = False) -> dict[str, Any]:
        result = await self.db.execute(
            select(ReconCampaign).where(
                ReconCampaign.id == campaign_id,
                ReconCampaign.organization_id == organization_id,
            ),
        )
        campaign = result.scalars().first()
        if not campaign:
            return {"organization_id": str(organization_id), "campaign_id": str(campaign_id), "status": "not_found"}

        campaign.status = "running" if approved else "awaiting_approval"
        await self.db.commit()

        return {
            "organization_id": str(organization_id),
            "campaign_id": str(campaign.id),
            "campaign_name": campaign.campaign_name,
            "status": campaign.status,
            "methodology": campaign.methodology or {},
            "executed_at": datetime.now(timezone.utc).isoformat(),
            "requires_human_approval": not approved,
        }

    async def evolve_campaign_strategy(self, organization_id: UUID, campaign_id: UUID, signals: dict[str, Any]) -> dict[str, Any]:
        result = await self.db.execute(
            select(ReconCampaign).where(
                ReconCampaign.id == campaign_id,
                ReconCampaign.organization_id == organization_id,
            ),
        )
        campaign = result.scalars().first()
        if not campaign:
            return {"organization_id": str(organization_id), "campaign_id": str(campaign_id), "status": "not_found"}

        evolved = adapt_hunt_strategy(
            {
                "campaign_name": campaign.campaign_name,
                "strategy_type": signals.get("strategy_type", "hunt"),
                "focus_areas": (campaign.methodology or {}).get("playbook", {}).get("focus_areas", []),
                "methodology": campaign.methodology or {},
            },
            signals,
        )
        campaign.methodology = evolved.get("methodology") or campaign.methodology
        campaign.status = "adapted"
        await self.db.commit()

        return {
            "organization_id": str(organization_id),
            "campaign_id": str(campaign.id),
            "campaign_name": campaign.campaign_name,
            "status": campaign.status,
            "methodology": campaign.methodology or {},
            "adaptive_notes": evolved.get("adaptive_notes"),
        }
