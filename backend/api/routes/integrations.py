"""
Integrations API routes: Bug bounty platform synchronization.
"""
from typing import Any, Dict, List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Path, status
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

@router.post("/bugcrowd/ingest", summary="Ingest Bugcrowd engagement with AI scope extraction")
async def ingest_bugcrowd_engagement(
    engagement_url: str = Query(..., description="Public Bugcrowd engagement URL"),
    organization_id: UUID = Query(..., description="Organization ID"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    rbac: RBACService = Depends(get_rbac),
) -> Dict[str, Any]:
    """
    Ingest a Bugcrowd public engagement page with AI-assisted scope extraction.
    
    Security:
    - Only accepts public engagement URLs
    - Rate limited to 2 requests per second
    - Validates URL domain is bugcrowd.com
    - Rejects private page access attempts
    - Normalizes and validates all targets
    
    Workflow:
    1. Fetch public engagement page
    2. Parse HTML with BeautifulSoup
    3. Extract scope with Claude AI
    4. Extract metadata (bounty, assets, auth)
    5. Normalize targets (domains, APIs, IPs)
    6. Validate targets with scope validator
    7. Store in Bugcrowd program model
    8. Link to asset inventory
    9. Generate recon workflows
    
    Args:
        engagement_url: Public Bugcrowd engagement URL
        organization_id: Organization workspace ID
        
    Returns:
        Ingestion result with imported assets
    """
    # Validate workspace access
    await _require_workspace(current_user.id, organization_id, rbac)
    await rbac.check_permission(current_user.id, organization_id, Permission.MANAGE_ASSETS)
    
    # Validate URL is public Bugcrowd
    if "bugcrowd.com" not in engagement_url.lower():
        raise HTTPException(
            status_code=400,
            detail="URL must be a Bugcrowd engagement page"
        )
    
    # Reject private paths
    private_paths = ["/settings", "/admin", "/account", "/api/", "?"]
    if any(path in engagement_url.lower() for path in private_paths):
        raise HTTPException(
            status_code=400,
            detail="Private or internal Bugcrowd URLs are not supported for security reasons"
        )
    
    try:
        from backend.services.bugcrowd_integration_service import BugcrowdIntegrationService
        from backend.ai.claude_client import ClaudeClient
        from backend.core.scope_validator import ScopeValidator
        
        # Initialize services
        claude = ClaudeClient()
        validator = ScopeValidator()
        ingestion_service = BugcrowdIntegrationService(claude, validator, db)
        
        # Run ingestion
        result = await ingestion_service.ingest_bugcrowd_engagement(
            engagement_url,
            str(organization_id)
        )
        
        if not result.success:
            raise HTTPException(
                status_code=400,
                detail=result.errors[0] if result.errors else "Ingestion failed"
            )
        
        return {
            "success": True,
            "program_name": result.program_name,
            "program_id": result.program_id,
            "assets_imported": result.assets_imported,
            "assets_updated": result.assets_updated,
            "duration_seconds": result.duration_seconds,
            "message": f"Successfully imported {result.assets_imported} assets from {result.program_name}"
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error ingesting Bugcrowd engagement: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to ingest Bugcrowd engagement: {str(e)}"
        )

@router.get("/bugcrowd/programs", summary="List ingested Bugcrowd programs")
async def list_bugcrowd_programs(
    organization_id: UUID = Query(..., description="Organization ID"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    rbac: RBACService = Depends(get_rbac),
) -> Dict[str, Any]:
    """List all Bugcrowd programs ingested for an organization."""
    from backend.models.bugcrowd_program import BugcrowdProgram
    
    await _require_workspace(current_user.id, organization_id, rbac)
    await rbac.check_permission(current_user.id, organization_id, Permission.VIEW_ASSETS)
    
    stmt = select(BugcrowdProgram).where(
        BugcrowdProgram.organization_id == str(organization_id)
    )
    result = await db.execute(stmt)
    programs = result.scalars().all()
    
    return {
        "programs": [
            {
                "id": p.id,
                "name": p.program_name,
                "engagement_url": p.engagement_url,
                "status": p.status,
                "assets_count": len(p.extracted_assets) if p.extracted_assets else 0,
                "last_synced_at": p.last_synced_at.isoformat() if p.last_synced_at else None,
                "created_at": p.created_at.isoformat(),
                "metadata": p.metadata
            } for p in programs
        ],
        "total": len(programs)
    }

@router.get("/bugcrowd/programs/{program_id}/assets", summary="List assets from Bugcrowd program")
async def list_bugcrowd_assets(
    program_id: str = Path(..., description="Bugcrowd program ID"),
    organization_id: UUID = Query(..., description="Organization ID"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    rbac: RBACService = Depends(get_rbac),
) -> Dict[str, Any]:
    """List all assets extracted from a Bugcrowd program."""
    from backend.models.bugcrowd_program import BugcrowdProgram
    
    await _require_workspace(current_user.id, organization_id, rbac)
    await rbac.check_permission(current_user.id, organization_id, Permission.VIEW_ASSETS)
    
    stmt = select(BugcrowdProgram).where(BugcrowdProgram.id == program_id)
    result = await db.execute(stmt)
    program = result.scalars().first()
    
    if not program or str(program.organization_id) != str(organization_id):
        raise HTTPException(status_code=404, detail="Program not found")
    
    return {
        "program_id": program.id,
        "program_name": program.program_name,
        "assets": [
            {
                "id": a.id,
                "target": a.target,
                "type": a.asset_type,
                "in_scope": a.in_scope,
                "wildcard": a.wildcard_pattern,
                "base_domain": a.base_domain,
                "priority": a.priority_level,
                "validation_status": a.validation_status
            } for a in program.extracted_assets
        ] if program.extracted_assets else [],
        "total": len(program.extracted_assets) if program.extracted_assets else 0
    }
