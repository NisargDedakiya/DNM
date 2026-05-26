"""
Collaboration API routes for shared investigations.
"""
from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from backend.auth.dependencies import get_current_user
from backend.core.permissions import Permission, RBACService
from backend.database.session import get_db
from backend.models.user import User
from backend.services.collaboration_service import CollaborationService
from backend.investigations.investigation_manager import InvestigationManager
from backend.collaboration.comment_engine import create_comment
from backend.collaboration.investigation_threads import add_comment
from backend.collaboration.team_assignments import assign_investigation


router = APIRouter(prefix="/collaboration", tags=["collaboration"])


class InvestigationCreateRequest(BaseModel):
    organization_id: UUID
    title: str = Field(..., min_length=3, max_length=255)
    severity: str = Field("medium", max_length=32)
    source_finding_id: UUID | None = None
    assigned_to: UUID | None = None
    summary: str | None = Field(None, max_length=4000)


class CommentCreateRequest(BaseModel):
    organization_id: UUID
    investigation_id: UUID
    content: str = Field(..., min_length=1, max_length=4000)
    parent_comment_id: UUID | None = None
    ai_reasoning: str | None = Field(None, max_length=4000)


class AssignmentCreateRequest(BaseModel):
    organization_id: UUID
    investigation_id: UUID
    assignee_id: UUID
    escalation_reason: str | None = Field(None, max_length=255)
    escalation_level: str | None = Field(None, max_length=32)


class EvidenceUploadRequest(BaseModel):
    organization_id: UUID
    investigation_id: UUID
    file_path: str = Field(..., min_length=1, max_length=2048)
    description: str = Field(..., min_length=1, max_length=2000)
    evidence_type: str = Field("note", max_length=32)
    metadata: dict[str, Any] | None = None


class EvidenceAttachRequest(BaseModel):
    organization_id: UUID
    investigation_id: UUID
    evidence_id: UUID
    description: str | None = Field(None, max_length=2000)
    metadata: dict[str, Any] | None = None


async def get_rbac(db: AsyncSession = Depends(get_db)) -> RBACService:
    return RBACService(db)


async def get_collaboration_service(db: AsyncSession = Depends(get_db)) -> CollaborationService:
    return CollaborationService(db)


async def get_investigations(db: AsyncSession = Depends(get_db)) -> InvestigationManager:
    return InvestigationManager(db)


async def _require_workspace(user_id: UUID, org_id: UUID, rbac: RBACService) -> None:
    await rbac.validate_workspace_access(user_id, org_id)


@router.post("/investigation", summary="Create an investigation workspace")
async def create_investigation_workspace(
    request: InvestigationCreateRequest,
    current_user: User = Depends(get_current_user),
    service: CollaborationService = Depends(get_collaboration_service),
    rbac: RBACService = Depends(get_rbac),
) -> dict[str, Any]:
    await _require_workspace(current_user.id, request.organization_id, rbac)
    await rbac.check_permission(current_user.id, request.organization_id, Permission.MANAGE_FINDINGS)
    return await service.create_investigation_workspace(
        organization_id=request.organization_id,
        title=request.title,
        severity=request.severity,
        created_by_id=current_user.id,
        source_finding_id=request.source_finding_id,
        assigned_to=request.assigned_to,
        summary=request.summary,
    )


@router.get("/investigations", summary="List collaborative investigations")
async def list_investigations(
    organization_id: UUID = Query(...),
    status: str | None = Query(None),
    severity: str | None = Query(None),
    current_user: User = Depends(get_current_user),
    investigations: InvestigationManager = Depends(get_investigations),
    rbac: RBACService = Depends(get_rbac),
) -> list[dict[str, Any]]:
    await _require_workspace(current_user.id, organization_id, rbac)
    await rbac.check_permission(current_user.id, organization_id, Permission.VIEW_FINDINGS)
    rows = await investigations.list_investigations(str(organization_id), status=status, severity=severity, limit=200)
    return [
        {
            "id": str(row.id),
            "organization_id": str(row.organization_id),
            "title": row.title,
            "severity": row.severity,
            "status": row.status,
            "assigned_to": str(row.assigned_to) if row.assigned_to else None,
            "source_finding_id": str(row.source_finding_id) if row.source_finding_id else None,
            "summary": row.summary,
            "workflow_stage": row.workflow_stage,
            "created_at": row.created_at.isoformat(),
        }
        for row in rows
    ]


@router.get("/investigation/{investigation_id}", summary="Get a collaboration workspace snapshot")
async def get_investigation_workspace(
    investigation_id: UUID,
    organization_id: UUID = Query(...),
    current_user: User = Depends(get_current_user),
    service: CollaborationService = Depends(get_collaboration_service),
    rbac: RBACService = Depends(get_rbac),
) -> dict[str, Any]:
    await _require_workspace(current_user.id, organization_id, rbac)
    await rbac.check_permission(current_user.id, organization_id, Permission.VIEW_FINDINGS)
    return await service.synchronize_team_updates(organization_id, investigation_id)


@router.post("/comment", summary="Add an investigation comment")
async def create_investigation_comment(
    request: CommentCreateRequest,
    current_user: User = Depends(get_current_user),
    service: CollaborationService = Depends(get_collaboration_service),
    rbac: RBACService = Depends(get_rbac),
) -> dict[str, Any]:
    await _require_workspace(current_user.id, request.organization_id, rbac)
    await rbac.check_permission(current_user.id, request.organization_id, Permission.MANAGE_FINDINGS)
    comment = await add_comment(
        service.db,
        investigation_id=request.investigation_id,
        author_id=current_user.id,
        content=request.content,
        parent_comment_id=request.parent_comment_id,
        ai_reasoning=request.ai_reasoning,
    )
    return comment


@router.post("/assign", summary="Assign an investigation")
async def assign_investigation_route(
    request: AssignmentCreateRequest,
    current_user: User = Depends(get_current_user),
    service: CollaborationService = Depends(get_collaboration_service),
    rbac: RBACService = Depends(get_rbac),
) -> dict[str, Any]:
    await _require_workspace(current_user.id, request.organization_id, rbac)
    await rbac.check_permission(current_user.id, request.organization_id, Permission.MANAGE_FINDINGS)
    assignment = await assign_investigation(
        service.db,
        investigation_id=request.investigation_id,
        assignee_id=request.assignee_id,
        assigned_by=current_user.id,
        escalation_reason=request.escalation_reason,
        escalation_level=request.escalation_level,
    )
    await service.notify_assignment_changes(request.organization_id, request.investigation_id, request.assignee_id, actor_id=current_user.id)
    return assignment


@router.post("/evidence", summary="Upload evidence for an investigation")
async def upload_investigation_evidence_route(
    request: EvidenceUploadRequest,
    current_user: User = Depends(get_current_user),
    service: CollaborationService = Depends(get_collaboration_service),
    rbac: RBACService = Depends(get_rbac),
) -> dict[str, Any]:
    await _require_workspace(current_user.id, request.organization_id, rbac)
    await rbac.check_permission(current_user.id, request.organization_id, Permission.MANAGE_FINDINGS)
    return await service.upload_investigation_evidence(
        organization_id=request.organization_id,
        investigation_id=request.investigation_id,
        file_path=request.file_path,
        description=request.description,
        uploaded_by_id=current_user.id,
        evidence_type=request.evidence_type,
        metadata=request.metadata,
    )


@router.post("/evidence/attach", summary="Attach an evidence version to an investigation")
async def attach_investigation_evidence_route(
    request: EvidenceAttachRequest,
    current_user: User = Depends(get_current_user),
    service: CollaborationService = Depends(get_collaboration_service),
    rbac: RBACService = Depends(get_rbac),
) -> dict[str, Any]:
    await _require_workspace(current_user.id, request.organization_id, rbac)
    await rbac.check_permission(current_user.id, request.organization_id, Permission.MANAGE_FINDINGS)
    return await service.attach_investigation_evidence(
        organization_id=request.organization_id,
        investigation_id=request.investigation_id,
        evidence_id=request.evidence_id,
        description=request.description,
        metadata=request.metadata,
    )
