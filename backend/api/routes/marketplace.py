"""
Marketplace API routes for plugins and enterprise integrations.
"""
from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from backend.auth.dependencies import get_current_user
from backend.core.permissions import Permission, RBACService
from backend.database.session import get_db
from backend.models.user import User
from backend.services.marketplace_service import MarketplaceService

router = APIRouter(prefix="/marketplace", tags=["marketplace"])


async def get_marketplace_service(db: AsyncSession = Depends(get_db)) -> MarketplaceService:
    return MarketplaceService(db)


async def get_rbac_service(db: AsyncSession = Depends(get_db)) -> RBACService:
    return RBACService(db)


class PluginInstallRequest(BaseModel):
    organization_id: UUID
    plugin_source: dict = Field(default_factory=dict)


class MarketplaceWorkflowRequest(BaseModel):
    organization_id: UUID
    workflow: dict = Field(default_factory=dict)


@router.get("/plugins")
async def list_plugins(
    organization_id: UUID = Query(..., description="Organisation workspace ID"),
    query: str | None = Query(None, description="Optional plugin search query"),
    current_user: User = Depends(get_current_user),
    service: MarketplaceService = Depends(get_marketplace_service),
    rbac: RBACService = Depends(get_rbac_service),
) -> dict:
    await rbac.validate_workspace_access(current_user.id, organization_id)
    await rbac.check_permission(current_user.id, organization_id, Permission.VIEW_ASSETS)
    plugins = await service.registry.search_marketplace(organization_id, query=query)
    return {
        "organization_id": str(organization_id),
        "plugins": plugins,
        "total": len(plugins),
    }


@router.post("/install", status_code=status.HTTP_201_CREATED)
async def install_plugin(
    request: PluginInstallRequest,
    current_user: User = Depends(get_current_user),
    service: MarketplaceService = Depends(get_marketplace_service),
    rbac: RBACService = Depends(get_rbac_service),
) -> dict:
    await rbac.validate_workspace_access(current_user.id, request.organization_id)
    await rbac.check_permission(current_user.id, request.organization_id, Permission.MANAGE_ORG)
    return await service.install_plugin(
        organization_id=request.organization_id,
        user_id=current_user.id,
        plugin_source=request.plugin_source,
    )


@router.get("/connectors")
async def list_connectors(
    organization_id: UUID = Query(..., description="Organisation workspace ID"),
    current_user: User = Depends(get_current_user),
    service: MarketplaceService = Depends(get_marketplace_service),
    rbac: RBACService = Depends(get_rbac_service),
) -> dict:
    await rbac.validate_workspace_access(current_user.id, organization_id)
    await rbac.check_permission(current_user.id, organization_id, Permission.VIEW_ASSETS)
    return await service.list_connectors(organization_id)


@router.post("/workflow")
async def execute_workflow(
    request: MarketplaceWorkflowRequest,
    current_user: User = Depends(get_current_user),
    service: MarketplaceService = Depends(get_marketplace_service),
    rbac: RBACService = Depends(get_rbac_service),
) -> dict:
    await rbac.validate_workspace_access(current_user.id, request.organization_id)
    await rbac.check_permission(current_user.id, request.organization_id, Permission.MANAGE_ORG)
    return await service.execute_marketplace_workflow(request.organization_id, request.workflow)
