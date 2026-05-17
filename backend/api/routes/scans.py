"""
Scan management API routes with JWT protection.
Handles scan lifecycle operations.
"""
import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.auth.dependencies import get_current_user
from backend.database.session import get_db
from backend.models.user import User
from backend.schemas.scan import (
    ScanCreate,
    ScanListResponse,
    ScanResponse,
    ScanExecutionRequest,
)
from backend.services.scan_service import ScanService
from backend.scanners.scanner_manager import ScannerManager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/scans", tags=["scans"])
scanner_manager = ScannerManager()


@router.post(
    "/start",
    response_model=ScanResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Start new scan",
    description="Initialize scan on program with full recon pipeline",
)
async def start_scan(
    request: ScanExecutionRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ScanResponse:
    """
    Start new scan on program.

    Triggers async recon pipeline: subfinder → httpx

    Args:
        request: Scan execution request
        current_user: Authenticated user
        db: Database session

    Returns:
        Created Scan record

    Raises:
        404: Program not found
        401: Unauthorized
        422: Invalid request
    """
    from backend.services.program_service import ProgramService

    # Verify program exists and user owns it
    program = await ProgramService.get_program_by_id(
        db,
        request.program_id,
        current_user.id,
    )

    if not program:
        logger.warning(
            f"Program not found: {request.program_id} for user {current_user.id}"
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Program not found",
        )

    try:
        # Create scan record
        scan = await ScanService.create_scan(
            db,
            program_id=request.program_id,
            user_id=current_user.id,
            scan_type=request.scan_type,
        )

        await db.commit()
        await db.refresh(scan)

        logger.info(
            f"Created scan {scan.id} for program {request.program_id} "
            f"by user {current_user.id}"
        )

        # TODO: Trigger async scan execution in background task
        # For now, return created scan record

        return ScanResponse.model_validate(scan)

    except Exception as exc:
        await db.rollback()
        logger.error(f"Failed to create scan: {exc}")
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Scan creation failed: {str(exc)}",
        )


@router.get(
    "",
    response_model=ScanListResponse,
    status_code=status.HTTP_200_OK,
    summary="List program scans",
    description="Get all scans for a program",
)
async def list_program_scans(
    program_id: UUID,
    limit: int = 100,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ScanListResponse:
    """
    List all scans for a program.

    Args:
        program_id: Program to list scans for
        limit: Maximum number of results
        current_user: Authenticated user
        db: Database session

    Returns:
        List of scan records with count

    Raises:
        404: Program not found
        401: Unauthorized
    """
    from backend.services.program_service import ProgramService

    # Verify program exists and user owns it
    program = await ProgramService.get_program_by_id(
        db,
        program_id,
        current_user.id,
    )

    if not program:
        logger.warning(f"Program not found: {program_id} for user {current_user.id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Program not found",
        )

    try:
        scans = await ScanService.get_program_scans(
            db,
            program_id=program_id,
            user_id=current_user.id,
            limit=limit,
        )

        return ScanListResponse(
            total=len(scans),
            scans=[ScanResponse.model_validate(scan) for scan in scans],
        )

    except Exception as exc:
        logger.error(f"Failed to list scans: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve scans",
        )


@router.get(
    "/{scan_id}",
    response_model=ScanResponse,
    status_code=status.HTTP_200_OK,
    summary="Get scan details",
    description="Retrieve specific scan record with status",
)
async def get_scan(
    scan_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ScanResponse:
    """
    Get scan details.

    Args:
        scan_id: Scan ID to retrieve
        current_user: Authenticated user
        db: Database session

    Returns:
        Scan record

    Raises:
        404: Scan not found
        401: Unauthorized
    """
    try:
        scan = await ScanService.get_scan_by_id(db, scan_id, current_user.id)

        if not scan:
            logger.warning(f"Scan not found: {scan_id} for user {current_user.id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Scan not found",
            )

        return ScanResponse.model_validate(scan)

    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"Failed to get scan: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve scan",
        )


@router.delete(
    "/{scan_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Cancel scan",
    description="Cancel and delete scan record",
)
async def cancel_scan(
    scan_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """
    Cancel and delete scan.

    Args:
        scan_id: Scan ID to cancel
        current_user: Authenticated user
        db: Database session

    Raises:
        404: Scan not found
        401: Unauthorized
    """
    try:
        deleted = await ScanService.delete_scan(db, scan_id, current_user.id)

        if not deleted:
            logger.warning(
                f"Scan not found for deletion: {scan_id} for user {current_user.id}"
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Scan not found",
            )

        await db.commit()
        logger.info(f"Deleted scan {scan_id} by user {current_user.id}")

    except HTTPException:
        raise
    except Exception as exc:
        await db.rollback()
        logger.error(f"Failed to delete scan: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete scan",
        )
