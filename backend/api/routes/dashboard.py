"""
Dashboard API routes providing analytics and KPIs.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.auth.dependencies import get_current_user
from backend.database.session import get_db
from backend.models.user import User
from backend.services import dashboard_service
from backend.schemas.dashboard import (
    DashboardStatsResponse,
    SeverityBreakdownResponse,
    ScanAnalyticsResponse,
    ActivityItem,
)

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/stats", response_model=DashboardStatsResponse)
async def dashboard_stats(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> DashboardStatsResponse:
    data = await dashboard_service.get_dashboard_stats(db, str(current_user.id))
    # convert recent_activity items to ActivityItem instances
    recent = [ActivityItem(**{"type": r["type"], "id": r["id"], "title": r.get("title"), "meta": r.get("meta", {}), "created_at": r["created_at"]}) for r in data.get("recent_activity", [])]
    return DashboardStatsResponse(
        total_programs=data.get("total_programs", 0),
        total_scans=data.get("total_scans", 0),
        total_findings=data.get("total_findings", 0),
        total_reports=data.get("total_reports", 0),
        findings_by_severity=data.get("findings_by_severity", {}),
        active_scans=data.get("active_scans", 0),
        recent_activity=recent,
    )


@router.get("/activity", response_model=list[ActivityItem])
async def dashboard_activity(limit: int = 20, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> list[ActivityItem]:
    data = await dashboard_service.get_recent_activity(db, str(current_user.id), limit=limit)
    return [ActivityItem(**{"type": r["type"], "id": r["id"], "title": r.get("title"), "meta": r.get("meta", {}), "created_at": r["created_at"]}) for r in data]


@router.get("/findings-breakdown", response_model=SeverityBreakdownResponse)
async def findings_breakdown(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> SeverityBreakdownResponse:
    data = await dashboard_service.get_findings_breakdown(db, str(current_user.id))
    return SeverityBreakdownResponse(breakdown=data)


@router.get("/scans", response_model=ScanAnalyticsResponse)
async def scans_analytics(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> ScanAnalyticsResponse:
    data = await dashboard_service.get_scan_statistics(db, str(current_user.id))
    return ScanAnalyticsResponse(
        counts_by_status=data.get("counts_by_status", {}),
        counts_by_type=data.get("counts_by_type", {}),
        avg_duration_seconds=data.get("avg_duration_seconds"),
    )
