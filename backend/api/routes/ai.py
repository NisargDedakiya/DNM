"""
AI endpoints for triage and report generation.

POST /ai/triage
POST /ai/report
"""
from __future__ import annotations

import logging
from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.auth.dependencies import get_current_user
from backend.database.session import get_db
from backend.models.user import User
from backend.services.finding_service import FindingService
from backend.ai import triage_service, report_service
from backend.schemas.ai import (
    TriageRequest,
    TriageResponse,
    ReportRequest,
    ReportResponse,
    ReportItem,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ai", tags=["ai"])


@router.post("/triage", response_model=TriageResponse)
async def ai_triage(
    req: TriageRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> TriageResponse:
    # load finding and validate ownership
    finding = await FindingService.get_finding_by_id(db, req.finding_id, current_user.id)
    if not finding:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Finding not found")

    result = await triage_service.triage_finding(
        title=finding.title,
        severity=(finding.severity.value if hasattr(finding.severity, "value") else str(finding.severity)),
        description=finding.description,
        endpoint=finding.endpoint,
        evidence=finding.evidence,
    )

    return TriageResponse(
        recommended_severity=result.severity,
        explanation=result.explanation,
        remediation=result.remediation,
        confidence=result.confidence,
    )


@router.post("/report", response_model=ReportResponse)
async def ai_report(
    req: ReportRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ReportResponse:
    # generate reports and persist
    reports = await report_service.generate_summary(req.finding_ids, db, current_user.id)
    await db.commit()

    items: List[ReportItem] = []
    for r in reports:
        items.append(ReportItem(finding_id=r.finding_id, report_id=r.id, content=r.content))

    return ReportResponse(reports=items)


@router.post("/strategy-plan")
async def generate_strategy_plan(
    org_id: str,
    program_name: str,
    tech_stack: str,
    endpoints: List[str],
    current_user: User = Depends(get_current_user)
):
    from backend.ai.core.ai_strategy_planner import ai_strategy_planner
    plan = await ai_strategy_planner.generate_hunt_plan(org_id, program_name, tech_stack, endpoints)
    return plan

