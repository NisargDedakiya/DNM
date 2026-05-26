"""
Strategy API routes for hunt planning and campaign intelligence.
"""
from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from backend.auth.dependencies import get_current_user
from backend.core.permissions import Permission, RBACService
from backend.database.session import get_db
from backend.models.user import User
from backend.services.strategy_service import StrategyService

router = APIRouter(prefix="/strategy", tags=["strategy"])


async def get_strategy_service(db: AsyncSession = Depends(get_db)) -> StrategyService:
    return StrategyService(db)


async def get_rbac_service(db: AsyncSession = Depends(get_db)) -> RBACService:
    return RBACService(db)


async def _authorize(current_user: User, organization_id: UUID, rbac: RBACService) -> None:
    await rbac.validate_workspace_access(current_user.id, organization_id)
    await rbac.check_permission(current_user.id, organization_id, Permission.RUN_SCANS)


@router.get("/hunts")
async def list_hunts(
    organization_id: UUID = Query(..., description="Organisation workspace ID"),
    current_user: User = Depends(get_current_user),
    strategy_service: StrategyService = Depends(get_strategy_service),
    rbac: RBACService = Depends(get_rbac_service),
) -> dict:
    await _authorize(current_user, organization_id, rbac)
    summary = await strategy_service.generate_strategy_summary(organization_id)
    return {
        "organization_id": str(organization_id),
        "hunts": summary.get("hunts", []),
        "strategy_memory": summary.get("strategy_memory", {}),
        "ai_note": summary.get("ai_note"),
    }


@router.get("/campaigns")
async def list_campaigns(
    organization_id: UUID = Query(..., description="Organisation workspace ID"),
    current_user: User = Depends(get_current_user),
    strategy_service: StrategyService = Depends(get_strategy_service),
    rbac: RBACService = Depends(get_rbac_service),
) -> dict:
    await _authorize(current_user, organization_id, rbac)
    return await strategy_service.correlate_campaign_intelligence(organization_id)


@router.get("/priorities")
async def list_priorities(
    organization_id: UUID = Query(..., description="Organisation workspace ID"),
    current_user: User = Depends(get_current_user),
    strategy_service: StrategyService = Depends(get_strategy_service),
    rbac: RBACService = Depends(get_rbac_service),
) -> dict:
    await _authorize(current_user, organization_id, rbac)
    summary = await strategy_service.generate_strategy_summary(organization_id)
    return {
        "organization_id": str(organization_id),
        "prioritized_targets": summary.get("targets", []),
        "strategy_memory": summary.get("strategy_memory", {}),
    }


@router.get("/recommendations")
async def list_recommendations(
    organization_id: UUID = Query(..., description="Organisation workspace ID"),
    current_user: User = Depends(get_current_user),
    strategy_service: StrategyService = Depends(get_strategy_service),
    rbac: RBACService = Depends(get_rbac_service),
) -> dict:
    await _authorize(current_user, organization_id, rbac)
    intelligence = await strategy_service.correlate_campaign_intelligence(organization_id)
    return {
        "organization_id": str(organization_id),
        "recommendations": intelligence.get("follow_up_recommendations", []),
        "attack_intelligence": intelligence.get("attack_intelligence", {}),
    }
