"""
Integrations API routes: Bug bounty platform synchronization.
"""
from typing import Any, Dict, List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.auth.dependencies import get_current_user
from backend.database.session import get_db
from backend.models.user import User
from backend.models.platform_program import PlatformProgram
from backend.core.permissions import Permission, RBACService
from backend.services.platform_sync_service import PlatformSyncService

router = APIRouter(prefix="/integrations", tags=["integrations"])

import logging
logger = logging.getLogger(__name__)

async def get_rbac(db: AsyncSession = Depends(get_db)) -> RBACService:
    return RBACService(db)

async def get_platform_sync_svc(db: AsyncSession = Depends(get_db)) -> PlatformSyncService:
    return PlatformSyncService(db)

async def _require_workspace(user_id: UUID, org_id: UUID, rbac: RBACService) -> None:
    await rbac.validate_workspace_access(user_id, org_id)

@router.post("/hackerone/sync", summary="Sync HackerOne programs")
async def sync_hackerone(
    organization_id: UUID = Query(..., description="Organization ID"),
    current_user: User = Depends(get_current_user),
    sync_svc: PlatformSyncService = Depends(get_platform_sync_svc),
    rbac: RBACService = Depends(get_rbac),
) -> Dict[str, Any]:
    """Sync programs and scopes from HackerOne."""
    await _require_workspace(current_user.id, organization_id, rbac)
    await rbac.check_permission(current_user.id, organization_id, Permission.MANAGE_ASSETS)
    
    result = await sync_svc.sync_hackerone_programs(organization_id)
    if result["status"] == "error":
        raise HTTPException(status_code=500, detail=result["message"])
    return result

@router.post("/bugcrowd/sync", summary="Sync Bugcrowd programs")
async def sync_bugcrowd(
    organization_id: UUID = Query(..., description="Organization ID"),
    current_user: User = Depends(get_current_user),
    sync_svc: PlatformSyncService = Depends(get_platform_sync_svc),
    rbac: RBACService = Depends(get_rbac),
) -> Dict[str, Any]:
    """Sync programs and scopes from Bugcrowd."""
    await _require_workspace(current_user.id, organization_id, rbac)
    await rbac.check_permission(current_user.id, organization_id, Permission.MANAGE_ASSETS)
    
    result = await sync_svc.sync_bugcrowd_programs(organization_id)
    return result

@router.get("/programs", summary="List integrated programs")
async def list_programs(
    organization_id: UUID = Query(..., description="Organization ID"),
    platform: str = Query(None, description="Filter by platform"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    rbac: RBACService = Depends(get_rbac),
) -> Dict[str, Any]:
    """List imported platform programs."""
    await _require_workspace(current_user.id, organization_id, rbac)
    await rbac.check_permission(current_user.id, organization_id, Permission.VIEW_ASSETS)
    
    stmt = select(PlatformProgram).where(PlatformProgram.organization_id == organization_id)
    if platform:
        stmt = stmt.where(PlatformProgram.platform_name == platform)
        
    result = await db.execute(stmt)
    programs = result.scalars().all()
    
    return {
        "programs": [
            {
                "id": str(p.id),
                "platform": p.platform_name,
                "name": p.program_name,
                "handle": p.program_handle,
                "url": p.program_url,
                "is_private": p.is_private,
                "offers_bounty": p.offers_bounty,
                "sync_status": p.sync_status,
                "synced_at": p.synced_at.isoformat() if p.synced_at else None
            } for p in programs
        ],
        "total": len(programs)
    }

@router.get("/scopes", summary="List integrated scopes")
async def list_scopes(
    program_id: UUID = Query(..., description="PlatformProgram ID"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    rbac: RBACService = Depends(get_rbac),
) -> Dict[str, Any]:
    """List scopes for a specific imported program."""
    stmt = select(PlatformProgram).where(PlatformProgram.id == program_id)
    result = await db.execute(stmt)
    program = result.scalars().first()
    
    if not program:
        raise HTTPException(status_code=404, detail="Program not found")
        
    await _require_workspace(current_user.id, program.organization_id, rbac)
    await rbac.check_permission(current_user.id, program.organization_id, Permission.VIEW_ASSETS)
    
    return {
        "program_id": str(program.id),
        "platform": program.platform_name,
        "scope_data": program.scope_data or {}
    }
