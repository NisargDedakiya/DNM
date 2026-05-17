"""
JWT-protected REST API routes for finding management.
"""
import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from backend.auth.dependencies import get_current_user
from backend.core.enums import FindingSeverity, FindingStatus
from backend.database.session import get_db
from backend.models.user import User
from backend.schemas.finding import (
    DeduplicateRequest,
    FindingCreate,
    FindingListResponse,
    FindingResponse,
    FindingUpdate,
)
from backend.services.finding_service import FindingService
from backend.services.program_service import ProgramService
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/findings", tags=["findings"])


@router.post(
    "",
    response_model=FindingResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create new finding",
)
async def create_finding(
    finding_data: FindingCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> FindingResponse:
    """
    Create new security finding.

    **Requirements:**
    - JWT authentication required
    - User must own the program
    - Title must be 3-255 characters
    - Description must be 10-10000 characters

    **Returns:**
    - 201 Created: Finding created successfully
    - 401 Unauthorized: Invalid token
    - 404 Not Found: Program not found
    - 422 Unprocessable Entity: Validation error
    """
    # Verify program ownership
    program = await ProgramService.get_program_by_id(
        db, finding_data.program_id, current_user.id
    )

    if not program:
        logger.warning(
            f"User {current_user.id} attempted to create finding "
            f"for non-existent program {finding_data.program_id}"
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Program not found",
        )

    # Check for duplicates
    duplicates = await FindingService.find_duplicates(
        db,
        finding_data.program_id,
        finding_data.title,
        finding_data.severity,
        finding_data.endpoint,
    )

    if duplicates:
        logger.info(
            f"Found {len(duplicates)} potential duplicates for finding: "
            f"{finding_data.title}"
        )

    # Create finding
    finding = await FindingService.create_finding(
        db,
        title=finding_data.title,
        description=finding_data.description,
        severity=finding_data.severity,
        program_id=finding_data.program_id,
        user_id=current_user.id,
        endpoint=finding_data.endpoint,
        evidence=finding_data.evidence,
        scan_id=finding_data.scan_id,
    )

    await db.commit()
    await db.refresh(finding)

    logger.info(
        f"Finding {finding.id} created by user {current_user.id} "
        f"({finding.severity}): {finding.title}"
    )

    return FindingResponse.from_orm(finding)


@router.get(
    "",
    response_model=FindingListResponse,
    summary="List findings",
)
async def list_findings(
    program_id: UUID = Query(..., description="Program ID"),
    severity: FindingSeverity | None = Query(
        default=None, description="Filter by severity"
    ),
    status: FindingStatus | None = Query(default=None, description="Filter by status"),
    scan_id: UUID | None = Query(default=None, description="Filter by scan"),
    limit: int = Query(default=100, ge=1, le=1000, description="Max results"),
    offset: int = Query(default=0, ge=0, description="Result offset"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> FindingListResponse:
    """
    List findings for program.

    **Features:**
    - Filters by severity, status, scan
    - Pagination support
    - Ownership validated
    - Ordered by created_at DESC

    **Returns:**
    - 200 OK: List of findings
    - 401 Unauthorized: Invalid token
    - 404 Not Found: Program not found
    """
    # Verify program ownership
    program = await ProgramService.get_program_by_id(db, program_id, current_user.id)

    if not program:
        logger.warning(
            f"User {current_user.id} attempted to list findings "
            f"for non-existent program {program_id}"
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Program not found",
        )

    # Get filtered findings
    findings, total = await FindingService.get_program_findings(
        db,
        program_id,
        current_user.id,
        severity=severity,
        status=status,
        scan_id=scan_id,
        limit=limit,
        offset=offset,
    )

    logger.debug(
        f"User {current_user.id} retrieved {len(findings)} findings "
        f"from program {program_id}"
    )

    return FindingListResponse(
        total=total,
        findings=[FindingResponse.from_orm(f) for f in findings],
    )


@router.get(
    "/{finding_id}",
    response_model=FindingResponse,
    summary="Get finding details",
)
async def get_finding(
    finding_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> FindingResponse:
    """
    Retrieve finding details.

    **Requirements:**
    - JWT authentication required
    - User must own the finding (through program)

    **Returns:**
    - 200 OK: Finding details
    - 401 Unauthorized: Invalid token
    - 404 Not Found: Finding not found or not owned
    """
    finding = await FindingService.get_finding_by_id(db, finding_id, current_user.id)

    if not finding:
        logger.warning(
            f"User {current_user.id} attempted to access finding {finding_id}"
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Finding not found",
        )

    logger.debug(f"User {current_user.id} retrieved finding {finding_id}")

    return FindingResponse.from_orm(finding)


@router.put(
    "/{finding_id}",
    response_model=FindingResponse,
    summary="Update finding",
)
async def update_finding(
    finding_id: UUID,
    update_data: FindingUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> FindingResponse:
    """
    Update finding details.

    **Features:**
    - Partial updates supported
    - Status can be changed
    - Severity can be escalated/downgraded
    - Ownership validated

    **Returns:**
    - 200 OK: Updated finding
    - 401 Unauthorized: Invalid token
    - 404 Not Found: Finding not found
    - 422 Unprocessable Entity: Validation error
    """
    finding = await FindingService.update_finding(
        db,
        finding_id,
        current_user.id,
        title=update_data.title,
        description=update_data.description,
        severity=update_data.severity,
        endpoint=update_data.endpoint,
        evidence=update_data.evidence,
        status=update_data.status,
    )

    if not finding:
        logger.warning(
            f"User {current_user.id} attempted to update finding {finding_id}"
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Finding not found",
        )

    await db.commit()
    await db.refresh(finding)

    logger.info(f"Finding {finding_id} updated by user {current_user.id}")

    return FindingResponse.from_orm(finding)


@router.delete(
    "/{finding_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete finding",
)
async def delete_finding(
    finding_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """
    Delete finding.

    **Requirements:**
    - JWT authentication required
    - User must own the finding

    **Returns:**
    - 204 No Content: Finding deleted
    - 401 Unauthorized: Invalid token
    - 404 Not Found: Finding not found
    """
    success = await FindingService.delete_finding(db, finding_id, current_user.id)

    if not success:
        logger.warning(
            f"User {current_user.id} attempted to delete finding {finding_id}"
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Finding not found",
        )

    await db.commit()

    logger.info(f"Finding {finding_id} deleted by user {current_user.id}")


@router.post(
    "/check-duplicates",
    summary="Check for duplicate findings",
)
async def check_duplicates(
    request: DeduplicateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Check for potential duplicate findings.

    Uses title, severity, and endpoint for matching.

    **Returns:**
    - 200 OK: Duplicate check results
    - 401 Unauthorized: Invalid token
    """
    # Verify program ownership
    program = await ProgramService.get_program_by_id(
        db, request.program_id, current_user.id
    )

    if not program:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Program not found",
        )

    duplicates = await FindingService.find_duplicates(
        db,
        request.program_id,
        request.title,
        request.severity,
        request.endpoint,
    )

    return {
        "count": len(duplicates),
        "duplicates": [
            {
                "id": str(d.id),
                "title": d.title,
                "severity": d.severity.value,
                "status": d.status.value,
                "created_at": d.created_at.isoformat(),
            }
            for d in duplicates
        ],
        "has_duplicates": len(duplicates) > 0,
    }


@router.get(
    "/{program_id}/summary",
    summary="Get findings summary",
)
async def get_findings_summary(
    program_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Get summary statistics for findings.

    **Includes:**
    - Count by severity
    - Count by status
    - Total critical findings

    **Returns:**
    - 200 OK: Summary statistics
    - 401 Unauthorized: Invalid token
    - 404 Not Found: Program not found
    """
    # Verify program ownership
    program = await ProgramService.get_program_by_id(db, program_id, current_user.id)

    if not program:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Program not found",
        )

    severity_summary = await FindingService.get_severity_summary(
        db, program_id, current_user.id
    )
    status_summary = await FindingService.get_status_summary(
        db, program_id, current_user.id
    )
    critical_count = await FindingService.count_critical_findings(
        db, program_id, current_user.id
    )

    return {
        "program_id": str(program_id),
        "severity_summary": severity_summary,
        "status_summary": status_summary,
        "critical_findings": critical_count,
        "total_findings": sum(severity_summary.values()),
    }
