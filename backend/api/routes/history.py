"""
Historical intelligence API routes.
"""
from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from backend.auth.dependencies import get_current_user
from backend.core.permissions import Permission, RBACService
from backend.database.session import get_db
from backend.models.user import User
from backend.services.history_service import HistoryService

router = APIRouter(prefix="/history", tags=["history"])


async def get_history_service(db: AsyncSession = Depends(get_db)) -> HistoryService:
    return HistoryService(db)


async def get_rbac_service(db: AsyncSession = Depends(get_db)) -> RBACService:
    return RBACService(db)


async def _enforce_workspace(user_id: UUID, organization_id: UUID, rbac: RBACService) -> None:
    await rbac.validate_workspace_access(user_id, organization_id)


@router.get("/hunts", summary="Historical hunt memory")
async def get_hunt_history(
    organization_id: UUID = Query(..., description="Organisation workspace ID"),
    query: str = Query("", description="Search query for related memory"),
    limit: int = Query(10, ge=1, le=50),
    current_user: User = Depends(get_current_user),
    history_service: HistoryService = Depends(get_history_service),
    rbac: RBACService = Depends(get_rbac_service),
) -> dict[str, Any]:
    await _enforce_workspace(current_user.id, organization_id, rbac)
    await rbac.check_permission(current_user.id, organization_id, Permission.VIEW_ASSETS)

    if query:
        return await history_service.retrieve_historical_context(organization_id, query, limit=limit)

    return await history_service.generate_history_summary(organization_id, limit=limit)


@router.get("/findings", summary="Historical findings intelligence")
async def get_findings_history(
    organization_id: UUID = Query(..., description="Organisation workspace ID"),
    limit: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    history_service: HistoryService = Depends(get_history_service),
    rbac: RBACService = Depends(get_rbac_service),
) -> dict[str, Any]:
    await _enforce_workspace(current_user.id, organization_id, rbac)
    await rbac.check_permission(current_user.id, organization_id, Permission.VIEW_FINDINGS)
    return await history_service.findings_history.track_recurring_findings(organization_id, limit=limit)


@router.get("/exposure", summary="Historical exposure intelligence")
async def get_exposure_history(
    organization_id: UUID = Query(..., description="Organisation workspace ID"),
    asset: str | None = Query(None, description="Optional asset filter"),
    limit: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    history_service: HistoryService = Depends(get_history_service),
    rbac: RBACService = Depends(get_rbac_service),
) -> dict[str, Any]:
    await _enforce_workspace(current_user.id, organization_id, rbac)
    await rbac.check_permission(current_user.id, organization_id, Permission.VIEW_FINDINGS)

    if asset:
        return await history_service.exposure_history.analyze_asset_evolution(organization_id, asset, limit=limit)

    return await history_service.exposure_history.detect_exposure_patterns(organization_id, limit=limit)


@router.get("/risk-trends", summary="Historical risk trends")
async def get_risk_trends(
    organization_id: UUID = Query(..., description="Organisation workspace ID"),
    limit: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    history_service: HistoryService = Depends(get_history_service),
    rbac: RBACService = Depends(get_rbac_service),
) -> dict[str, Any]:
    await _enforce_workspace(current_user.id, organization_id, rbac)
    await rbac.check_permission(current_user.id, organization_id, Permission.VIEW_ASSETS)
    return await history_service.analyze_org_risk_evolution(organization_id, limit=limit)

