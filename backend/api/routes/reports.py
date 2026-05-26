from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.auth.dependencies import get_current_user
from backend.database.session import get_db
from backend.models.user import User
from backend.models.report import Report
from backend.models.finding import Finding
from backend.models.program import Program
from backend.services.report_writer_service import report_writer
from backend.schemas.report import (
    ReportGenerateRequest,
    ReportUpdateRequest,
    ReportResponse,
)

router = APIRouter(prefix="/reports", tags=["reports"])


@router.post("/generate", response_model=ReportResponse, status_code=status.HTTP_201_CREATED)
async def generate_report(
    body: ReportGenerateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Generate a HackerOne formatted bug report from a finding.
    """
    finding = await db.get(Finding, body.finding_id)
    if not finding:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Finding not found")

    if finding.organization_id:
        from backend.core.permissions import RBACService
        rbac = RBACService(db)
        await rbac.validate_workspace_access(current_user.id, finding.organization_id)

    try:
        report = await report_writer.generate(
            db=db,
            finding_id=body.finding_id,
            evidence_notes=body.evidence_notes,
            platform=body.platform,
        )
        return report
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate report: {str(e)}"
        )


@router.get("/{id}", response_model=ReportResponse)
async def get_report(
    id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get a full report record.
    """
    report = await db.get(Report, id)
    if not report:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")

    finding = await db.get(Finding, report.finding_id)
    if finding and finding.organization_id:
        from backend.core.permissions import RBACService
        rbac = RBACService(db)
        await rbac.validate_workspace_access(current_user.id, finding.organization_id)

    return report


@router.put("/{id}", response_model=ReportResponse)
async def update_report(
    id: UUID,
    body: ReportUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Update editable report fields.
    """
    report = await db.get(Report, id)
    if not report:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")

    finding = await db.get(Finding, report.finding_id)
    if finding and finding.organization_id:
        from backend.core.permissions import RBACService
        rbac = RBACService(db)
        await rbac.validate_workspace_access(current_user.id, finding.organization_id)

    # Perform updates
    if body.title is not None:
        report.title = body.title
    if body.severity is not None:
        report.severity = body.severity
    if body.vulnerability_type is not None:
        report.vulnerability_type = body.vulnerability_type
    if body.description is not None:
        report.description = body.description
    if body.steps_to_reproduce is not None:
        report.steps_to_reproduce = body.steps_to_reproduce
    if body.impact is not None:
        report.impact = body.impact
    if body.remediation is not None:
        report.remediation = body.remediation
    if body.cvss_score is not None:
        report.cvss_score = body.cvss_score
    if body.quality_score is not None:
        report.quality_score = body.quality_score
    if body.quality_breakdown is not None:
        report.quality_breakdown = body.quality_breakdown

    await db.commit()
    await db.refresh(report)
    return report


@router.post("/{id}/submit")
async def submit_report(
    id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Submit report to HackerOne.
    """
    report = await db.get(Report, id)
    if not report:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")

    finding = await db.get(Finding, report.finding_id)
    if finding and finding.organization_id:
        from backend.core.permissions import RBACService
        rbac = RBACService(db)
        await rbac.validate_workspace_access(current_user.id, finding.organization_id)

    program = await db.get(Program, finding.program_id)
    if not program or not program.handle:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Program has no valid HackerOne handle configured for submission"
        )

    try:
        submission_id = await report_writer.submit_to_hackerone(db, id, program.handle)
        return {"submission_id": submission_id, "status": "submitted"}
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Submission failed: {str(e)}"
        )
