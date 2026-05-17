"""
Copilot API routes: AI Security Copilot and investigation workspace endpoints.

All routes:
- Require JWT authentication.
- Enforce workspace isolation via RBAC.
- Cap user input at 800 chars (double-sanitised by CopilotEngine).
- Return only structured JSON — no raw AI text.
- Carry explicit advisory metadata in every response.

Route map
---------
POST /copilot/chat            → contextual AI chat with organisation context
GET  /copilot/asset/{id}      → AI intelligence summary for an asset
GET  /copilot/exposure/{id}   → AI explanation for an exposure
POST /copilot/investigate     → full guided investigation workflow
GET  /copilot/context/asset/{id}     → raw context for an asset (no AI)
GET  /copilot/context/exposure/{id}  → raw context for an exposure (no AI)
GET  /copilot/context/graph          → graph topology context
GET  /copilot/history                → historical change context
POST /copilot/investigate/report     → generate final investigation summary
"""
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Body, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.ext.asyncio import AsyncSession

from backend.auth.dependencies import get_current_user
from backend.database.session import get_db
from backend.models.user import User
from backend.core.permissions import Permission, RBACService
from backend.services.context_service import ContextService
from backend.services.investigation_service import InvestigationService
from backend.ai.copilot_engine import CopilotEngine
from backend.ai.investigation_assistant import InvestigationAssistant

router = APIRouter(prefix="/copilot", tags=["copilot"])

import logging
logger = logging.getLogger(__name__)


# ── Request models ─────────────────────────────────────────────────────────────

class ChatRequest(BaseModel):
    """Analyst chat message request."""
    organization_id: UUID = Field(..., description="Workspace ID")
    message: str = Field(..., min_length=1, max_length=800, description="Analyst question (max 800 chars)")
    context_type: str | None = Field(None, description="Context type: asset | exposure | finding | graph")
    context_entity_id: UUID | None = Field(None, description="Entity ID for context (optional)")

    @field_validator("message")
    @classmethod
    def strip_control_chars(cls, v: str) -> str:
        import re
        return re.sub(r"[\x00-\x1f\x7f]", " ", v).strip()


class InvestigateRequest(BaseModel):
    """Investigation trigger request."""
    organization_id: UUID = Field(..., description="Workspace ID")
    investigation_type: str = Field(..., description="asset | exposure | finding")
    entity_id: UUID = Field(..., description="Entity to investigate")
    analyst_note: str | None = Field(None, max_length=400, description="Optional analyst context note")


class InvestigationReportRequest(BaseModel):
    """Request to generate a final investigation summary."""
    organization_id: UUID = Field(..., description="Workspace ID")
    investigation_data: dict = Field(..., description="Full investigation package from POST /copilot/investigate")


# ── Dependency helpers ──────────────────────────────────────────────────────────

async def get_rbac(db: AsyncSession = Depends(get_db)) -> RBACService:
    return RBACService(db)


async def get_context_svc(db: AsyncSession = Depends(get_db)) -> ContextService:
    return ContextService(db)


async def get_investigation_svc(db: AsyncSession = Depends(get_db)) -> InvestigationService:
    return InvestigationService(db)


async def get_engine() -> CopilotEngine:
    return CopilotEngine()


async def get_assistant(db: AsyncSession = Depends(get_db)) -> InvestigationAssistant:
    return InvestigationAssistant(db)


async def _require_workspace(user_id: UUID, org_id: UUID, rbac: RBACService) -> None:
    await rbac.validate_workspace_access(user_id, org_id)


# ============================================================================
# COPILOT CHAT
# ============================================================================

@router.post(
    "/chat",
    summary="AI Security Copilot chat",
    description=(
        "Send a natural-language security question to the AI Copilot with "
        "optional entity context. The copilot assembles relevant intelligence "
        "and returns structured, advisory-only analysis.\n\n"
        "**Message is capped at 800 characters** and sanitised before embedding.\n"
        "All responses include `advisory_note` and `requires_human_review: true`."
    ),
)
async def copilot_chat(
    request: ChatRequest,
    current_user: User = Depends(get_current_user),
    ctx_svc: ContextService = Depends(get_context_svc),
    engine: CopilotEngine = Depends(get_engine),
    rbac: RBACService = Depends(get_rbac),
) -> dict[str, Any]:
    """
    Contextual AI security copilot chat.

    **Requires**: VIEW_ASSETS permission.

    The copilot assembles context (if entity_id provided), sends the
    message to the AI engine, and returns structured JSON with explanation,
    key findings, recommendations, and follow-up questions.
    """
    await _require_workspace(current_user.id, request.organization_id, rbac)
    await rbac.check_permission(current_user.id, request.organization_id, Permission.VIEW_ASSETS)

    # Assemble context if entity specified
    context: dict[str, Any] = {}
    if request.context_entity_id and request.context_type:
        if request.context_type == "asset":
            context = await ctx_svc.get_asset_context(
                request.organization_id, request.context_entity_id
            )
        elif request.context_type == "exposure":
            context = await ctx_svc.get_exposure_context(
                request.organization_id, request.context_entity_id
            )
        elif request.context_type == "finding":
            context = await ctx_svc.get_finding_context(
                request.organization_id, request.context_entity_id
            )
        elif request.context_type == "graph":
            context = await ctx_svc.get_graph_context(request.organization_id)
    else:
        # Organisation-level graph context as default
        context = await ctx_svc.get_graph_context(request.organization_id)

    response = await engine.generate_copilot_response(
        user_message=request.message,
        context=context,
    )

    return {
        "query": request.message[:100] + "..." if len(request.message) > 100 else request.message,
        "organization_id": str(request.organization_id),
        "context_type": request.context_type,
        "context_entity_id": str(request.context_entity_id) if request.context_entity_id else None,
        **response,
    }


# ============================================================================
# ASSET AI INTELLIGENCE
# ============================================================================

@router.get(
    "/asset/{asset_id}",
    summary="AI intelligence summary for an asset",
    description=(
        "Assembles a comprehensive AI-generated intelligence summary for an asset: "
        "risk assessment, technology risks, exposure priorities, attack surface summary, "
        "and investigation recommendations. Advisory only."
    ),
)
async def get_asset_intelligence(
    asset_id: UUID,
    organization_id: UUID = Query(..., description="Organisation workspace ID"),
    current_user: User = Depends(get_current_user),
    ctx_svc: ContextService = Depends(get_context_svc),
    engine: CopilotEngine = Depends(get_engine),
    rbac: RBACService = Depends(get_rbac),
) -> dict[str, Any]:
    """
    AI intelligence summary for an asset.

    **Requires**: VIEW_ASSETS permission.
    """
    await _require_workspace(current_user.id, organization_id, rbac)
    await rbac.check_permission(current_user.id, organization_id, Permission.VIEW_ASSETS)

    context = await ctx_svc.get_asset_context(organization_id, asset_id)

    if "error" in context:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=context["error"],
        )

    ai_summary = await engine.summarize_asset_intelligence(context)

    return {
        "asset_id": str(asset_id),
        "organization_id": str(organization_id),
        "context_summary": {
            "hostname": context.get("entity_summary", {}).get("hostname"),
            "risk_score": context.get("entity_summary", {}).get("risk_score"),
            "active_exposures": context.get("related_data", {}).get("active_exposure_count", 0),
            "technologies": context.get("related_data", {}).get("technology_count", 0),
        },
        "ai_intelligence": ai_summary,
    }


# ============================================================================
# EXPOSURE AI EXPLANATION
# ============================================================================

@router.get(
    "/exposure/{exposure_id}",
    summary="AI explanation for an exposure",
    description=(
        "Generates a structured AI explanation for a specific exposure: "
        "executive summary, technical explanation, business impact, attack vectors, "
        "and remediation steps. Advisory only — requires human review."
    ),
)
async def get_exposure_explanation(
    exposure_id: UUID,
    organization_id: UUID = Query(..., description="Organisation workspace ID"),
    current_user: User = Depends(get_current_user),
    ctx_svc: ContextService = Depends(get_context_svc),
    engine: CopilotEngine = Depends(get_engine),
    rbac: RBACService = Depends(get_rbac),
) -> dict[str, Any]:
    """
    AI-powered exposure explanation.

    **Requires**: VIEW_FINDINGS permission.
    """
    await _require_workspace(current_user.id, organization_id, rbac)
    await rbac.check_permission(current_user.id, organization_id, Permission.VIEW_FINDINGS)

    context = await ctx_svc.get_exposure_context(organization_id, exposure_id)

    if "error" in context:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=context["error"],
        )

    ai_explanation = await engine.explain_exposure(context)

    return {
        "exposure_id": str(exposure_id),
        "organization_id": str(organization_id),
        "exposure_summary": context.get("entity_summary", {}),
        "ai_explanation": ai_explanation,
    }


# ============================================================================
# GUIDED INVESTIGATION
# ============================================================================

@router.post(
    "/investigate",
    status_code=status.HTTP_200_OK,
    summary="Start a guided AI investigation",
    description=(
        "Triggers a full AI-assisted investigation for an asset, exposure, or finding. "
        "Assembles context → AI analysis → investigation checklist → graph intelligence "
        "→ historical context. **All output is advisory and requires human review.**"
    ),
)
async def start_investigation(
    request: InvestigateRequest,
    current_user: User = Depends(get_current_user),
    inv_svc: InvestigationService = Depends(get_investigation_svc),
    rbac: RBACService = Depends(get_rbac),
) -> dict[str, Any]:
    """
    Full guided investigation workflow.

    **Requires**: VIEW_FINDINGS permission (investigations involve sensitive data).

    Returns a complete investigation package with:
    - `context`             — assembled entity intelligence
    - `ai_analysis`         — AI-generated explanation (advisory)
    - `investigation_steps` — ordered analyst checklist
    - `graph_intelligence`  — risk propagation + neighbourhood
    - `historical_context`  — 14-day change event summary
    """
    await _require_workspace(current_user.id, request.organization_id, rbac)
    await rbac.check_permission(current_user.id, request.organization_id, Permission.VIEW_FINDINGS)

    valid_types = {"asset", "exposure", "finding"}
    if request.investigation_type not in valid_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid investigation_type. Valid: {sorted(valid_types)}",
        )

    try:
        result = await inv_svc.start_investigation(
            organization_id=request.organization_id,
            investigation_type=request.investigation_type,
            entity_id=request.entity_id,
            analyst_note=request.analyst_note,
        )
    except Exception as exc:
        logger.error("Investigation failed: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Investigation failed: {exc}",
        ) from exc

    return result


# ============================================================================
# RAW CONTEXT ENDPOINTS (no AI — for UI context panels)
# ============================================================================

@router.get(
    "/context/asset/{asset_id}",
    summary="Raw asset context (no AI)",
    description="Returns the assembled investigation context for an asset without AI analysis. Useful for context panels.",
)
async def get_asset_context(
    asset_id: UUID,
    organization_id: UUID = Query(..., description="Organisation workspace ID"),
    current_user: User = Depends(get_current_user),
    ctx_svc: ContextService = Depends(get_context_svc),
    rbac: RBACService = Depends(get_rbac),
) -> dict[str, Any]:
    """Raw asset context. **Requires**: VIEW_ASSETS."""
    await _require_workspace(current_user.id, organization_id, rbac)
    await rbac.check_permission(current_user.id, organization_id, Permission.VIEW_ASSETS)

    ctx = await ctx_svc.get_asset_context(organization_id, asset_id)
    if "error" in ctx:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=ctx["error"])
    return ctx


@router.get(
    "/context/exposure/{exposure_id}",
    summary="Raw exposure context (no AI)",
    description="Returns the assembled investigation context for an exposure without AI analysis.",
)
async def get_exposure_context(
    exposure_id: UUID,
    organization_id: UUID = Query(..., description="Organisation workspace ID"),
    current_user: User = Depends(get_current_user),
    ctx_svc: ContextService = Depends(get_context_svc),
    rbac: RBACService = Depends(get_rbac),
) -> dict[str, Any]:
    """Raw exposure context. **Requires**: VIEW_FINDINGS."""
    await _require_workspace(current_user.id, organization_id, rbac)
    await rbac.check_permission(current_user.id, organization_id, Permission.VIEW_FINDINGS)

    ctx = await ctx_svc.get_exposure_context(organization_id, exposure_id)
    if "error" in ctx:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=ctx["error"])
    return ctx


@router.get(
    "/context/graph",
    summary="Graph topology context",
    description="Returns graph node/edge statistics and top-connected nodes for the organisation.",
)
async def get_graph_context(
    organization_id: UUID = Query(..., description="Organisation workspace ID"),
    current_user: User = Depends(get_current_user),
    ctx_svc: ContextService = Depends(get_context_svc),
    rbac: RBACService = Depends(get_rbac),
) -> dict[str, Any]:
    """Graph topology context. **Requires**: VIEW_ASSETS."""
    await _require_workspace(current_user.id, organization_id, rbac)
    await rbac.check_permission(current_user.id, organization_id, Permission.VIEW_ASSETS)

    return await ctx_svc.get_graph_context(organization_id)


@router.get(
    "/history",
    summary="Historical change intelligence",
    description="Returns recent change event history and risk trend direction for the organisation.",
)
async def get_historical_context(
    organization_id: UUID = Query(..., description="Organisation workspace ID"),
    days: int = Query(14, ge=1, le=90, description="Rolling window in days"),
    current_user: User = Depends(get_current_user),
    ctx_svc: ContextService = Depends(get_context_svc),
    rbac: RBACService = Depends(get_rbac),
) -> dict[str, Any]:
    """Historical change intelligence. **Requires**: VIEW_ASSETS."""
    await _require_workspace(current_user.id, organization_id, rbac)
    await rbac.check_permission(current_user.id, organization_id, Permission.VIEW_ASSETS)

    return await ctx_svc.retrieve_historical_context(organization_id, days=days)


# ============================================================================
# INVESTIGATION REPORT
# ============================================================================

@router.post(
    "/investigate/report",
    summary="Generate final investigation summary report",
    description=(
        "Takes the output of POST /copilot/investigate and generates a "
        "final structured investigation summary report. Advisory only."
    ),
)
async def generate_investigation_report(
    request: InvestigationReportRequest,
    current_user: User = Depends(get_current_user),
    inv_svc: InvestigationService = Depends(get_investigation_svc),
    rbac: RBACService = Depends(get_rbac),
) -> dict[str, Any]:
    """
    Final investigation summary.

    **Requires**: VIEW_FINDINGS permission.
    """
    await _require_workspace(current_user.id, request.organization_id, rbac)
    await rbac.check_permission(current_user.id, request.organization_id, Permission.VIEW_FINDINGS)

    try:
        return await inv_svc.generate_investigation_report(
            organization_id=request.organization_id,
            investigation_data=request.investigation_data,
        )
    except Exception as exc:
        logger.error("Investigation report failed: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Investigation report generation failed: {exc}",
        ) from exc
