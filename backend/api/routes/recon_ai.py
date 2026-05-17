"""
AI recon planning API routes.

All endpoints are JWT-protected, workspace-isolated, and return
advisory-only AI outputs. No autonomous scan execution occurs here.

Routes:
  POST /ai/recon-plan       — Generate AI recon plan
  GET  /ai/recommendations  — Get next-action recommendations
  GET  /ai/high-value-assets — Get high-value asset priorities
  POST /ai/workflow-preview — Preview an AI-generated workflow
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from backend.auth.dependencies import get_current_user
from backend.database.session import get_db
from backend.models.user import User
from backend.services.recon_strategy_service import ReconStrategyService
from backend.services.asset_priority_service import AssetPriorityService
from backend.ai.workflow_engine import build_workflow, recommend_next_stage

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ai", tags=["ai-recon"])


# ── Request / Response schemas ────────────────────────────────

class ReconPlanRequest(BaseModel):
    organization_id: UUID = Field(..., description="Organization workspace ID")
    program_id: Optional[UUID] = Field(None, description="Optional program scope")
    program_name: str = Field("Unnamed Program", description="Human-readable program name")
    scope_domains: List[str] = Field(default_factory=list, description="In-scope domain list")


class WorkflowPreviewRequest(BaseModel):
    organization_id: UUID = Field(..., description="Organization workspace ID")
    program_id: Optional[UUID] = Field(None, description="Optional program scope")
    program_name: str = Field("Preview Program", description="Program name for workflow")
    scope_domains: List[str] = Field(default_factory=list, description="In-scope domains")
    asset_types: List[str] = Field(default_factory=list, description="Asset types present")
    risk_level: str = Field("medium", description="Current risk level")
    technologies: List[str] = Field(default_factory=list, description="Known technologies")
    existing_coverage: List[str] = Field(default_factory=list, description="Already covered scan types")


class AdvisoryResponse(BaseModel):
    """Base response indicating advisory-only AI output."""
    advisory_note: str = Field(
        default="This output is AI-generated and advisory-only. Human review and approval is required."
    )
    status: str = Field(default="pending_human_review")


def _enforce_workspace(current_user: User, organization_id: UUID) -> None:
    """
    Enforce workspace isolation.
    Users can only access their own organization data.
    """
    user_org = getattr(current_user, "organization_id", None)
    if user_org is not None and str(user_org) != str(organization_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: workspace isolation enforced",
        )


# ── Endpoints ─────────────────────────────────────────────────

@router.post(
    "/recon-plan",
    summary="Generate AI Recon Plan",
    description=(
        "Generates an AI-assisted recon plan based on current asset intelligence, "
        "exposure analytics, and findings history. Output is advisory-only. "
        "Human approval required before execution."
    ),
)
async def create_recon_plan(
    req: ReconPlanRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """
    Generate a structured AI recon plan.

    - **JWT required**: Bearer token in Authorization header
    - **Workspace isolated**: organization_id must match authenticated user
    - **Advisory only**: No scan execution occurs
    - **Human approval**: plan.status == 'pending_human_review'
    """
    _enforce_workspace(current_user, req.organization_id)

    service = ReconStrategyService(db)
    try:
        strategy = await service.create_recon_strategy(
            organization_id=req.organization_id,
            program_id=req.program_id,
            program_name=req.program_name,
            scope_domains=req.scope_domains,
        )
    except Exception as exc:
        logger.exception("Recon plan generation failed for org %s: %s", req.organization_id, exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Recon plan generation failed. Please try again.",
        )

    return strategy


@router.get(
    "/recommendations",
    summary="Get AI Recommendations",
    description=(
        "Returns prioritized next-action, asset focus, and follow-up scan "
        "recommendations based on current attack surface intelligence. "
        "All recommendations are advisory only."
    ),
)
async def get_recommendations(
    organization_id: UUID = Query(..., description="Organization workspace ID"),
    program_id: Optional[UUID] = Query(None, description="Optional program scope"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """
    Get AI-powered next-action recommendations.

    - **JWT required**
    - **Workspace isolated**
    - **Advisory only** — no actions are taken automatically
    """
    _enforce_workspace(current_user, organization_id)

    service = ReconStrategyService(db)
    try:
        recommendations = await service.generate_recommendations(
            organization_id=organization_id,
            program_id=program_id,
        )
    except Exception as exc:
        logger.exception("Recommendation generation failed for org %s: %s", organization_id, exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Recommendation generation failed.",
        )

    return {
        "organization_id": str(organization_id),
        "program_id": str(program_id) if program_id else None,
        "recommendations": recommendations,
        "advisory_note": "All recommendations are AI-generated and advisory-only.",
        "status": "pending_human_review",
    }


@router.get(
    "/high-value-assets",
    summary="Get High-Value Assets",
    description=(
        "Returns risk-prioritized list of high-value assets identified by "
        "multi-factor exposure scoring. Includes recon depth recommendations "
        "and gap analysis."
    ),
)
async def get_high_value_assets(
    organization_id: UUID = Query(..., description="Organization workspace ID"),
    program_id: Optional[UUID] = Query(None, description="Optional program scope"),
    min_priority: str = Query("high", description="Minimum priority level: critical|high|medium|low"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """
    Identify and rank high-value recon targets.

    - **JWT required**
    - **Workspace isolated**
    - Returns multi-factor priority scores with score breakdown
    """
    _enforce_workspace(current_user, organization_id)

    valid_levels = {"critical", "high", "medium", "low", "info"}
    if min_priority not in valid_levels:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"min_priority must be one of {sorted(valid_levels)}",
        )

    service = AssetPriorityService(db)
    try:
        result = await service.identify_high_value_assets(
            organization_id=organization_id,
            program_id=program_id,
            min_priority_level=min_priority,
        )
    except Exception as exc:
        logger.exception("High-value asset identification failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Asset priority calculation failed.",
        )

    return {
        "organization_id": str(organization_id),
        "program_id": str(program_id) if program_id else None,
        **result,
    }


@router.post(
    "/workflow-preview",
    summary="Preview AI Workflow",
    description=(
        "Generates a preview of an AI-recommended recon workflow pipeline. "
        "All stages are marked as requiring human approval. "
        "No execution occurs — preview only."
    ),
)
async def workflow_preview(
    req: WorkflowPreviewRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """
    Preview an AI-generated recon workflow.

    - **JWT required**
    - **Workspace isolated**
    - **Preview only** — workflow.status == 'pending_review'
    - All stages have requires_approval == True
    """
    _enforce_workspace(current_user, req.organization_id)

    try:
        workflow = await build_workflow(
            program_name=req.program_name,
            scope_domains=req.scope_domains,
            asset_types=req.asset_types,
            risk_level=req.risk_level,
            technologies=req.technologies,
            existing_coverage=req.existing_coverage,
            program_id=req.program_id,
        )
    except Exception as exc:
        logger.exception("Workflow preview generation failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Workflow generation failed.",
        )

    return {
        "organization_id": str(req.organization_id),
        "program_id": str(req.program_id) if req.program_id else None,
        "preview": True,
        "workflow": workflow,
        "security_note": (
            "This workflow is AI-generated and for preview only. "
            "Each stage requires explicit human approval before execution. "
            "No autonomous scanning will occur."
        ),
    }
