"""
Performance optimization and platform hardening routes.
"""
from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from backend.auth.dependencies import get_current_user
from backend.core.permissions import Permission, RBACService
from backend.database.session import get_db
from backend.models.user import User
from backend.services.performance_service import PerformanceService

router = APIRouter(prefix="/performance", tags=["performance"])


async def get_performance_service(db: AsyncSession = Depends(get_db)) -> PerformanceService:
    return PerformanceService(db)


async def get_rbac(db: AsyncSession = Depends(get_db)) -> RBACService:
    return RBACService(db)


async def _require_workspace(user_id: UUID, organization_id: UUID, rbac: RBACService) -> None:
    await rbac.validate_workspace_access(user_id, organization_id)


@router.get("/overview", summary="Platform performance overview")
async def get_performance_overview(
    organization_id: UUID,
    current_user: User = Depends(get_current_user),
    performance_service: PerformanceService = Depends(get_performance_service),
    rbac: RBACService = Depends(get_rbac),
) -> dict[str, Any]:
    await _require_workspace(current_user.id, organization_id, rbac)
    await rbac.check_permission(current_user.id, organization_id, Permission.MANAGE_SCANS)
    return await performance_service.generate_performance_summary(organization_id)


@router.get("/websocket", summary="WebSocket performance metrics")
async def get_websocket_performance(
    organization_id: UUID,
    current_user: User = Depends(get_current_user),
    performance_service: PerformanceService = Depends(get_performance_service),
    rbac: RBACService = Depends(get_rbac),
) -> dict[str, Any]:
    await _require_workspace(current_user.id, organization_id, rbac)
    await rbac.check_permission(current_user.id, organization_id, Permission.MANAGE_SCANS)
    return await performance_service.get_websocket_metrics(organization_id)


@router.get("/ai", summary="AI performance metrics")
async def get_ai_performance(
    organization_id: UUID,
    current_user: User = Depends(get_current_user),
    performance_service: PerformanceService = Depends(get_performance_service),
    rbac: RBACService = Depends(get_rbac),
) -> dict[str, Any]:
    await _require_workspace(current_user.id, organization_id, rbac)
    await rbac.check_permission(current_user.id, organization_id, Permission.MANAGE_SCANS)
    return await performance_service.get_ai_metrics(organization_id)


@router.get("/queues", summary="Distributed queue metrics")
async def get_queue_performance(
    organization_id: UUID,
    current_user: User = Depends(get_current_user),
    performance_service: PerformanceService = Depends(get_performance_service),
    rbac: RBACService = Depends(get_rbac),
) -> dict[str, Any]:
    await _require_workspace(current_user.id, organization_id, rbac)
    await rbac.check_permission(current_user.id, organization_id, Permission.MANAGE_SCANS)
    return await performance_service.get_queue_metrics(organization_id)


@router.get("/graph", summary="Graph rendering performance metrics")
async def get_graph_performance(
    organization_id: UUID,
    current_user: User = Depends(get_current_user),
    performance_service: PerformanceService = Depends(get_performance_service),
    rbac: RBACService = Depends(get_rbac),
) -> dict[str, Any]:
    await _require_workspace(current_user.id, organization_id, rbac)
    await rbac.check_permission(current_user.id, organization_id, Permission.MANAGE_SCANS)
    return await performance_service.get_graph_metrics(organization_id)
