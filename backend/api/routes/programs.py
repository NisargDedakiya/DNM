"""
Program routes for CRUD operations.
Protected endpoints for managing bug bounty programs.
"""
from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, Response
from sqlalchemy.ext.asyncio import AsyncSession

from backend.schemas.program import (
    ProgramCreate,
    ProgramUpdate,
    ProgramResponse,
    ProgramListResponse,
)
from backend.database.session import get_db
from backend.services.program_service import ProgramService
from backend.auth.dependencies import get_current_user
from backend.models.user import User

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
        return ProgramResponse.from_attributes(program)
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
            ProgramResponse.from_attributes(prog) for prog in programs
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
        return ProgramResponse.from_attributes(program)
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
        return ProgramResponse.from_attributes(program)
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
