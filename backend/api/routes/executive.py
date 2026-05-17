"""
Executive API routes: executive risk intelligence and reporting endpoints.

All routes:
- Require JWT authentication.
- Enforce workspace isolation via RBAC validate_workspace_access.
- Return plain JSON (no ORM objects).
- Are async throughout.

Route map
---------
GET  /executive/dashboard        → executive dashboard with posture + insights
GET  /executive/posture          → detailed security posture scorecard
GET  /executive/trends           → risk trend analysis (configurable window)
GET  /executive/surface          → attack surface intelligence report
GET  /executive/insights         → C-suite intelligence bullets
GET  /executive/risk-summary     → concise risk summary widget data
POST /executive/reports          → generate and persist an executive report
GET  /executive/reports          → list historical reports (metadata)
GET  /executive/reports/{id}     → retrieve report metadata + data
GET  /executive/reports/{id}/export → retrieve sanitised Markdown export
"""
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import PlainTextResponse
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from backend.auth.dependencies import get_current_user
from backend.database.session import get_db
from backend.models.user import User
from backend.models.executive_report import ExecutiveReport, ExecutiveReportType
from backend.core.permissions import Permission, RBACService
from backend.services.executive_risk_service import ExecutiveRiskService
from backend.services.reporting_service import ReportingService
from backend.services.posture_service import PostureService

router = APIRouter(prefix="/executive", tags=["executive"])


# ── Dependency helpers ────────────────────────────────────────────────────────

async def get_rbac(db: AsyncSession = Depends(get_db)) -> RBACService:
    return RBACService(db)


async def get_exec_svc(db: AsyncSession = Depends(get_db)) -> ExecutiveRiskService:
    return ExecutiveRiskService(db)


async def get_reporting_svc(db: AsyncSession = Depends(get_db)) -> ReportingService:
    return ReportingService(db)


async def get_posture_svc(db: AsyncSession = Depends(get_db)) -> PostureService:
    return PostureService(db)


async def _require_workspace(user_id: UUID, org_id: UUID, rbac: RBACService) -> None:
    await rbac.validate_workspace_access(user_id, org_id)


# =============================================================================
# EXECUTIVE DASHBOARD
# =============================================================================

@router.get(
    "/dashboard",
    summary="Executive security dashboard",
    description=(
        "Returns the full executive dashboard payload: security posture score, "
        "exposure KPIs, C-suite insight bullets, attack surface summary, and "
        "risk trend direction — suitable for a single-page executive overview."
    ),
)
async def get_executive_dashboard(
    organization_id: UUID = Query(..., description="Organisation workspace ID"),
    current_user: User = Depends(get_current_user),
    exec_svc: ExecutiveRiskService = Depends(get_exec_svc),
    reporting_svc: ReportingService = Depends(get_reporting_svc),
    rbac: RBACService = Depends(get_rbac),
) -> dict[str, Any]:
    """
    Full executive dashboard payload.

    **Requires**: VIEW_ASSETS permission.

    Returns a composite payload with:
    - `posture`          — 0-100 score + grade + components
    - `exposure_summary` — severity breakdown + top exposures
    - `surface_growth`   — surface momentum + counts
    - `insights`         — critical / risk / positive intelligence bullets
    - `risk_summary`     — quick-glance widget data
    """
    await _require_workspace(current_user.id, organization_id, rbac)
    await rbac.check_permission(current_user.id, organization_id, Permission.VIEW_ASSETS)

    # Run intelligence gathering concurrently (await sequentially for simplicity
    # in this sync-friendly pattern; real deployment can use asyncio.gather)
    posture = await exec_svc.calculate_security_posture(organization_id)
    exposure_summary = await exec_svc.summarize_exposure_risk(organization_id, top_n=5)
    growth = await exec_svc.analyze_attack_surface_growth(organization_id, days=14)
    insights = await exec_svc.generate_executive_insights(organization_id)
    risk_summary = await reporting_svc.build_risk_summary(organization_id)

    return {
        "organization_id": str(organization_id),
        "posture": posture,
        "exposure_summary": exposure_summary,
        "surface_growth": growth,
        "insights": insights,
        "risk_summary": risk_summary,
    }


# =============================================================================
# SECURITY POSTURE
# =============================================================================

@router.get(
    "/posture",
    summary="Detailed security posture scorecard",
    description=(
        "Returns the full security posture score with per-component breakdown, "
        "attack surface KPIs, top action items, and posture summary narrative."
    ),
)
async def get_security_posture(
    organization_id: UUID = Query(..., description="Organisation workspace ID"),
    current_user: User = Depends(get_current_user),
    exec_svc: ExecutiveRiskService = Depends(get_exec_svc),
    rbac: RBACService = Depends(get_rbac),
) -> dict[str, Any]:
    """
    Detailed posture scorecard.

    **Requires**: VIEW_ASSETS permission.
    """
    await _require_workspace(current_user.id, organization_id, rbac)
    await rbac.check_permission(current_user.id, organization_id, Permission.VIEW_ASSETS)

    return await exec_svc.calculate_security_posture(organization_id)


# =============================================================================
# RISK TRENDS
# =============================================================================

@router.get(
    "/trends",
    summary="Risk trend analysis",
    description=(
        "Returns daily risk delta time-series, trend direction (improving / worsening / stable), "
        "and week-over-week comparison for the specified rolling window."
    ),
)
async def get_risk_trends(
    organization_id: UUID = Query(..., description="Organisation workspace ID"),
    days: int = Query(30, ge=7, le=365, description="Analysis window in days"),
    current_user: User = Depends(get_current_user),
    posture_svc: PostureService = Depends(get_posture_svc),
    rbac: RBACService = Depends(get_rbac),
) -> dict[str, Any]:
    """
    Risk trend time-series for dashboard charts.

    **Requires**: VIEW_FINDINGS permission.
    """
    await _require_workspace(current_user.id, organization_id, rbac)
    await rbac.check_permission(current_user.id, organization_id, Permission.VIEW_FINDINGS)

    return await posture_svc.analyze_risk_trends(organization_id, days=days)


# =============================================================================
# ATTACK SURFACE INTELLIGENCE
# =============================================================================

@router.get(
    "/surface",
    summary="Attack surface intelligence report",
    description=(
        "Returns a detailed attack surface intelligence payload including posture, "
        "exposure density, surface growth momentum, and executive insights."
    ),
)
async def get_attack_surface_intelligence(
    organization_id: UUID = Query(..., description="Organisation workspace ID"),
    program_id: UUID | None = Query(None, description="Optional program scope"),
    current_user: User = Depends(get_current_user),
    reporting_svc: ReportingService = Depends(get_reporting_svc),
    rbac: RBACService = Depends(get_rbac),
) -> dict[str, Any]:
    """
    Full attack surface intelligence report.

    **Requires**: VIEW_ASSETS permission.
    """
    await _require_workspace(current_user.id, organization_id, rbac)
    await rbac.check_permission(current_user.id, organization_id, Permission.VIEW_ASSETS)

    return await reporting_svc.generate_attack_surface_report(
        organization_id=organization_id,
        program_id=program_id,
    )


# =============================================================================
# EXECUTIVE INSIGHTS
# =============================================================================

@router.get(
    "/insights",
    summary="C-suite intelligence bullets",
    description=(
        "Generates narrative intelligence bullets for C-suite consumption: "
        "critical insights, risk-level insights, positive signals, and "
        "strategic recommendations."
    ),
)
async def get_executive_insights(
    organization_id: UUID = Query(..., description="Organisation workspace ID"),
    current_user: User = Depends(get_current_user),
    exec_svc: ExecutiveRiskService = Depends(get_exec_svc),
    rbac: RBACService = Depends(get_rbac),
) -> dict[str, Any]:
    """
    Executive intelligence bullets.

    **Requires**: VIEW_FINDINGS permission.
    """
    await _require_workspace(current_user.id, organization_id, rbac)
    await rbac.check_permission(current_user.id, organization_id, Permission.VIEW_FINDINGS)

    return await exec_svc.generate_executive_insights(organization_id)


# =============================================================================
# RISK SUMMARY WIDGET
# =============================================================================

@router.get(
    "/risk-summary",
    summary="Quick-glance risk summary widget",
    description="Concise risk summary: posture score, critical counts, surface momentum.",
)
async def get_risk_summary(
    organization_id: UUID = Query(..., description="Organisation workspace ID"),
    current_user: User = Depends(get_current_user),
    reporting_svc: ReportingService = Depends(get_reporting_svc),
    rbac: RBACService = Depends(get_rbac),
) -> dict[str, Any]:
    """
    Risk summary widget for dashboard panels.

    **Requires**: VIEW_ASSETS permission.
    """
    await _require_workspace(current_user.id, organization_id, rbac)
    await rbac.check_permission(current_user.id, organization_id, Permission.VIEW_ASSETS)

    return await reporting_svc.build_risk_summary(organization_id)


# =============================================================================
# GENERATE REPORT
# =============================================================================

@router.post(
    "/reports",
    status_code=status.HTTP_201_CREATED,
    summary="Generate and persist an executive report",
    description=(
        "Triggers intelligence collection and generates a new immutable "
        "ExecutiveReport row. Each call produces a new historical entry. "
        "Requires VIEW_ASSETS permission."
    ),
)
async def generate_report(
    organization_id: UUID = Query(..., description="Organisation workspace ID"),
    report_type: str = Query(
        ...,
        description=(
            "Report type: exposure_summary | attack_surface_report | "
            "executive_brief | risk_trends | posture_report"
        ),
    ),
    program_id: UUID | None = Query(None, description="Optional program scope"),
    custom_title: str | None = Query(None, description="Override auto-generated title"),
    current_user: User = Depends(get_current_user),
    reporting_svc: ReportingService = Depends(get_reporting_svc),
    rbac: RBACService = Depends(get_rbac),
) -> dict[str, Any]:
    """
    Generate a new executive report.

    **Requires**: VIEW_ASSETS permission.

    Returns report metadata (id, type, title, summary, created_at).
    """
    await _require_workspace(current_user.id, organization_id, rbac)
    await rbac.check_permission(current_user.id, organization_id, Permission.VIEW_ASSETS)

    # Validate report type
    try:
        rt = ExecutiveReportType(report_type)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid report_type '{report_type}'. Valid: {[t.value for t in ExecutiveReportType]}",
        )

    try:
        report = await reporting_svc.generate_executive_report(
            organization_id=organization_id,
            report_type=rt,
            generated_by=current_user.id,
            program_id=program_id,
            custom_title=custom_title,
        )
    except Exception as exc:
        logger.error("Report generation failed: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Report generation failed: {exc}",
        ) from exc

    return {
        "id": str(report.id),
        "report_type": report.report_type,
        "title": report.title,
        "summary": report.summary,
        "organization_id": str(report.organization_id),
        "generated_by": str(report.generated_by) if report.generated_by else None,
        "created_at": report.created_at.isoformat() if report.created_at else None,
    }


# =============================================================================
# LIST REPORTS
# =============================================================================

@router.get(
    "/reports",
    summary="List historical executive reports",
    description=(
        "Returns paginated metadata for all historical executive reports "
        "in the organisation workspace. Workspace isolation enforced."
    ),
)
async def list_reports(
    organization_id: UUID = Query(..., description="Organisation workspace ID"),
    report_type: str | None = Query(None, description="Filter by report type"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    reporting_svc: ReportingService = Depends(get_reporting_svc),
    rbac: RBACService = Depends(get_rbac),
) -> dict[str, Any]:
    """
    List historical executive reports.

    **Requires**: VIEW_ASSETS permission.
    """
    await _require_workspace(current_user.id, organization_id, rbac)
    await rbac.check_permission(current_user.id, organization_id, Permission.VIEW_ASSETS)

    rt = None
    if report_type:
        try:
            rt = ExecutiveReportType(report_type)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid report_type '{report_type}'. Valid: {[t.value for t in ExecutiveReportType]}",
            )

    return await reporting_svc.list_reports(
        organization_id=organization_id,
        report_type=rt,
        limit=limit,
        offset=offset,
    )


# =============================================================================
# GET REPORT BY ID
# =============================================================================

@router.get(
    "/reports/{report_id}",
    summary="Retrieve executive report by ID",
    description="Returns full report metadata and structured data payload.",
)
async def get_report(
    report_id: UUID,
    organization_id: UUID = Query(..., description="Organisation workspace ID"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    rbac: RBACService = Depends(get_rbac),
) -> dict[str, Any]:
    """
    Retrieve a report by ID (with workspace isolation).

    **Requires**: VIEW_ASSETS permission.
    """
    await _require_workspace(current_user.id, organization_id, rbac)
    await rbac.check_permission(current_user.id, organization_id, Permission.VIEW_ASSETS)

    stmt = select(ExecutiveReport).where(
        and_(
            ExecutiveReport.id == report_id,
            ExecutiveReport.organization_id == organization_id,
        )
    )
    result = await db.execute(stmt)
    report = result.scalars().first()

    if report is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Report not found or access denied.",
        )

    return {
        "id": str(report.id),
        "report_type": report.report_type,
        "title": report.title,
        "summary": report.summary,
        "report_data": report.report_data,
        "organization_id": str(report.organization_id),
        "program_id": str(report.program_id) if report.program_id else None,
        "generated_by": str(report.generated_by) if report.generated_by else None,
        "created_at": report.created_at.isoformat() if report.created_at else None,
    }


# =============================================================================
# EXPORT REPORT AS MARKDOWN
# =============================================================================

@router.get(
    "/reports/{report_id}/export",
    summary="Export report as sanitised Markdown",
    description=(
        "Returns the pre-rendered, sanitised Markdown content of a report "
        "suitable for download or email distribution."
    ),
    response_class=PlainTextResponse,
)
async def export_report_markdown(
    report_id: UUID,
    organization_id: UUID = Query(..., description="Organisation workspace ID"),
    current_user: User = Depends(get_current_user),
    reporting_svc: ReportingService = Depends(get_reporting_svc),
    rbac: RBACService = Depends(get_rbac),
) -> str:
    """
    Export a report as Markdown text.

    **Requires**: VIEW_ASSETS permission.

    Returns `text/plain` (sanitised Markdown).
    """
    await _require_workspace(current_user.id, organization_id, rbac)
    await rbac.check_permission(current_user.id, organization_id, Permission.VIEW_ASSETS)

    markdown = await reporting_svc.export_markdown_report(
        organization_id=organization_id,
        report_id=report_id,
    )
    if markdown is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Report not found or access denied.",
        )

    return markdown


import logging
logger = logging.getLogger(__name__)
