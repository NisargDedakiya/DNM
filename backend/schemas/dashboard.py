"""
Pydantic schemas for dashboard and analytics responses.
"""
from __future__ import annotations

from datetime import datetime
from pydantic import BaseModel, Field
from typing import Dict, List
from uuid import UUID


class ActivityItem(BaseModel):
    type: str
    id: UUID
    title: str | None = None
    meta: Dict[str, str] = {}
    created_at: datetime


class SeverityBreakdownResponse(BaseModel):
    breakdown: Dict[str, int]


class ScanAnalyticsResponse(BaseModel):
    counts_by_status: Dict[str, int]
    counts_by_type: Dict[str, int]
    avg_duration_seconds: float | None = None


class DashboardStatsResponse(BaseModel):
    total_programs: int
    total_scans: int
    total_findings: int
    total_reports: int
    findings_by_severity: Dict[str, int]
    active_scans: int
    recent_activity: List[ActivityItem]
