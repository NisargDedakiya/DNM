"""
Program routes for CRUD operations.
Protected endpoints for managing bug bounty programs.
"""
from __future__ import annotations

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.schemas.program import (
    ProgramCreate,
    ProgramUpdate,
    ProgramResponse,
    ProgramListResponse,
)
from backend.database.session import get_db
from backend.services.program_service import ProgramService
from backend.services.program_sync_service import ProgramSyncService
from backend.auth.dependencies import get_current_user
from backend.models.user import User
from backend.models.team_member import TeamMember
from backend.models.organization import Organization
from backend.models.program import Program
from pydantic import BaseModel
from backend.services.bugcrowd_scraper import bugcrowd_scraper, BugcrowdScrapeError, BugcrowdError

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/programs", tags=["programs"])


@router.post("", response_model=ProgramResponse, status_code=status.HTTP_201_CREATED)
async def create_program(
    payload: ProgramCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ProgramResponse:
    """
    Create a new program.

    Args:
        payload: Program creation data
        current_user: Currently authenticated user
        db: Database session

    Returns:
        ProgramResponse: Created program

    Raises:
        HTTPException: 401 Unauthorized, 400 Bad Request
    """
    try:
        svc = ProgramService(db)
        program = await svc.create_program(
            user_id=current_user.id,
            name=payload.name,
            platform=payload.platform,
            scope=payload.scope,
            description=payload.description,
        )
        return ProgramResponse.model_validate(program)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create program",
        )


@router.get("", response_model=ProgramListResponse)
async def list_programs(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ProgramListResponse:
    """
    List all programs owned by the current user.

    Args:
        current_user: Currently authenticated user
        db: Database session

    Returns:
        ProgramListResponse: List of user's programs with count

    Raises:
        HTTPException: 401 Unauthorized
    """
    try:
        svc = ProgramService(db)
        programs = await svc.get_user_programs(user_id=current_user.id)
        program_responses = [
            ProgramResponse.model_validate(prog) for prog in programs
        ]
        return ProgramListResponse(
            total=len(program_responses),
            programs=program_responses,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve programs",
        )


@router.get("/{program_id}", response_model=ProgramResponse)
async def get_program(
    program_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ProgramResponse:
    """
    Get a specific program by ID (must be owned by current user).

    Args:
        program_id: Program ID
        current_user: Currently authenticated user
        db: Database session

    Returns:
        ProgramResponse: Program details

    Raises:
        HTTPException: 401 Unauthorized, 404 Not Found
    """
    try:
        svc = ProgramService(db)
        program = await svc.get_program_by_id(
            program_id=program_id,
            user_id=current_user.id,
        )
        if not program:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Program not found",
            )
        return ProgramResponse.model_validate(program)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve program",
        )


@router.put("/{program_id}", response_model=ProgramResponse)
async def update_program(
    program_id: UUID,
    payload: ProgramUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ProgramResponse:
    """
    Update a program (must be owned by current user).

    Args:
        program_id: Program ID
        payload: Update data
        current_user: Currently authenticated user
        db: Database session

    Returns:
        ProgramResponse: Updated program

    Raises:
        HTTPException: 401 Unauthorized, 404 Not Found, 400 Bad Request
    """
    try:
        svc = ProgramService(db)
        program = await svc.update_program(
            program_id=program_id,
            user_id=current_user.id,
            name=payload.name,
            platform=payload.platform,
            scope=payload.scope,
            description=payload.description,
        )
        if not program:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Program not found",
            )
        return ProgramResponse.model_validate(program)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update program",
        )


@router.delete("/{program_id}", status_code=status.HTTP_204_NO_CONTENT, response_class=Response)
async def delete_program(
    program_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Delete a program (must be owned by current user).

    Args:
        program_id: Program ID
        current_user: Currently authenticated user
        db: Database session

    Raises:
        HTTPException: 401 Unauthorized, 404 Not Found
    """
    try:
        svc = ProgramService(db)
        deleted = await svc.delete_program(
            program_id=program_id,
            user_id=current_user.id,
        )
        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Program not found",
            )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete program",
        )


@router.post("/sync-hackerone")
async def sync_hackerone(
    organization_id: UUID | None = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Synchronize all HackerOne programs.
    """
    if not organization_id:
        # Fetch the first active organization membership of the user
        stmt = select(TeamMember.organization_id).where(
            TeamMember.user_id == current_user.id,
            TeamMember.is_active == True
        )
        res = await db.execute(stmt)
        organization_id = res.scalars().first()
        
        # If still None, look up any organizations owned by the user
        if not organization_id:
            stmt = select(Organization.id).where(Organization.owner_id == current_user.id)
            res = await db.execute(stmt)
            organization_id = res.scalars().first()
            
        if not organization_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User is not associated with any organization. Please specify organization_id."
            )
    else:
        # Validate workspace access
        from backend.core.permissions import RBACService
        rbac = RBACService(db)
        await rbac.validate_workspace_access(current_user.id, organization_id)

    svc = ProgramSyncService(db)
    try:
        result = await svc.sync_all(organization_id, current_user.id)
        return result
    except Exception as e:
        logger.error(f"Failed to sync HackerOne programs: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to sync HackerOne programs: {str(e)}"
        )


@router.post("/{program_id}/refresh-scope")
async def refresh_program_scope(
    program_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Refresh the scope for a specific program.
    """
    # Fetch program by program_id
    stmt = select(Program).where(Program.id == program_id)
    res = await db.execute(stmt)
    program = res.scalars().first()
    if not program:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Program not found"
        )
        
    # Check workspace access
    from backend.core.permissions import RBACService
    rbac = RBACService(db)
    await rbac.validate_workspace_access(current_user.id, program.organization_id)
    
    svc = ProgramSyncService(db)
    try:
        summary = await svc.refresh_scope(program_id, program.organization_id)
        return summary
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Failed to refresh program scope: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to refresh program scope: {str(e)}"
        )


class BugcrowdRequest(BaseModel):
    url: str


@router.post("/bugcrowd/preview")
async def preview_bugcrowd_program(
    payload: BugcrowdRequest,
    current_user: User = Depends(get_current_user),
):
    """
    Preview Bugcrowd program scope without saving it to database.
    Returns the AI-parsed scope dict for user to review before confirming.
    """
    try:
        scope = await bugcrowd_scraper.fetch_and_parse(payload.url)
        return scope
    except BugcrowdScrapeError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        )
    except Exception as exc:
        logger.error(f"Failed to preview Bugcrowd program: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to preview Bugcrowd program: {str(exc)}",
        )


@router.post("/bugcrowd/add", response_model=ProgramResponse, status_code=status.HTTP_201_CREATED)
async def add_bugcrowd_program(
    payload: BugcrowdRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ProgramResponse:
    """
    Scrape Bugcrowd program, create or update Program in database, and return it.
    """
    try:
        # Fetch the first active organization membership of the user
        stmt = select(TeamMember.organization_id).where(
            TeamMember.user_id == current_user.id,
            TeamMember.is_active == True
        )
        res = await db.execute(stmt)
        organization_id = res.scalars().first()
        
        # If still None, look up any organizations owned by the user
        if not organization_id:
            stmt = select(Organization.id).where(Organization.owner_id == current_user.id)
            res = await db.execute(stmt)
            organization_id = res.scalars().first()
            
        if not organization_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User is not associated with any organization. Please specify organization_id."
            )

        # Scrape using Bugcrowd Scraper
        result = await bugcrowd_scraper.fetch_and_parse(payload.url)
        
        handle = payload.url.rstrip('/').split('/')[-1]
        name = result.get('program_name') or handle
        
        # Format scope string from list of assets
        in_scope_assets = [t.get('asset', '') for t in result.get('in_scope', []) if t.get('asset')]
        scope_str = ", ".join(in_scope_assets) if in_scope_assets else "No in-scope targets"
        
        # Check if program already exists
        stmt = select(Program).where(
            Program.organization_id == organization_id,
            Program.platform == 'bugcrowd',
            Program.handle == handle
        )
        res = await db.execute(stmt)
        program = res.scalars().first()
        
        if program:
            program.name = name
            program.scope = scope_str
            program.scope_json = result
            program.is_active = True
        else:
            program = Program(
                name=name,
                platform='bugcrowd',
                scope=scope_str,
                description=f"Bugcrowd program from {payload.url}",
                created_by=current_user.id,
                organization_id=organization_id,
                handle=handle,
                is_private=result.get('vdp_only', False),
                scope_json=result,
                is_active=True,
            )
            db.add(program)
            
        await db.commit()
        await db.refresh(program)
        return ProgramResponse.model_validate(program)
        
    except BugcrowdScrapeError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        )
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"Failed to add Bugcrowd program: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to add Bugcrowd program: {str(exc)}",
        )
