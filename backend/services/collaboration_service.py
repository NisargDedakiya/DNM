"""
High-level collaboration orchestration for shared investigations.
"""
from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from backend.collaboration.evidence_manager import attach_evidence, retrieve_evidence, upload_evidence
from backend.collaboration.investigation_threads import add_comment, create_thread, retrieve_thread
from backend.collaboration.team_assignments import assign_investigation, track_assignment_status
from backend.core.events import EventType
from backend.investigations.investigation_manager import InvestigationManager
from backend.investigations.workflow_tracker import WorkflowTracker
from backend.services.event_service import event_service
from backend.services.notification_service import notification_service


class CollaborationService:
    """Coordinates investigation workspaces, comments, evidence, and assignments."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.investigations = InvestigationManager(db)
        self.workflow = WorkflowTracker(db)

    async def create_investigation_workspace(
        self,
        organization_id: UUID,
        title: str,
        severity: str,
        created_by_id: UUID,
        source_finding_id: UUID | None = None,
        assigned_to: UUID | None = None,
        summary: str | None = None,
    ) -> dict[str, Any]:
        investigation = await self.investigations.create_investigation(
            organization_id=str(organization_id),
            title=title,
            severity=severity,
            assigned_to=assigned_to,
            source_finding_id=source_finding_id,
            summary=summary,
        )

        thread = await create_thread(
            self.db,
            organization_id=str(organization_id),
            title=title,
            severity=severity,
            assigned_to=assigned_to,
            source_finding_id=source_finding_id,
            summary=summary,
            created_by_id=created_by_id,
        )

        assignment = None
        if assigned_to:
            assignment = await assign_investigation(
                self.db,
                investigation_id=investigation.id,
                assignee_id=assigned_to,
                assigned_by=created_by_id,
            )

        await event_service.emit_event(
            EventType.INVESTIGATION_CREATED,
            str(organization_id),
            {
                "investigation_id": str(investigation.id),
                "title": investigation.title,
                "severity": investigation.severity,
                "source_finding_id": str(source_finding_id) if source_finding_id else None,
                "created_by_id": str(created_by_id),
            },
        )
        await notification_service.send_collaboration_notification(
            str(organization_id),
            f"Investigation workspace created: {title}",
            {"investigation_id": str(investigation.id), "severity": severity},
        )

        return {
            "investigation": {
                "id": str(investigation.id),
                "organization_id": str(investigation.organization_id),
                "title": investigation.title,
                "severity": investigation.severity,
                "status": investigation.status,
                "assigned_to": str(investigation.assigned_to) if investigation.assigned_to else None,
                "summary": investigation.summary,
                "workflow_stage": investigation.workflow_stage,
                "created_at": investigation.created_at.isoformat(),
            },
            "thread": thread,
            "assignment": assignment,
        }

    async def synchronize_team_updates(self, organization_id: UUID, investigation_id: UUID) -> dict[str, Any]:
        thread = await retrieve_thread(self.db, investigation_id, str(organization_id))
        evidence = await retrieve_evidence(self.db, investigation_id)
        assignment = await track_assignment_status(self.db, investigation_id)
        return {
            "organization_id": str(organization_id),
            "investigation_id": str(investigation_id),
            "thread": thread,
            "evidence": evidence,
            "assignment": assignment,
        }

    async def notify_assignment_changes(self, organization_id: UUID, investigation_id: UUID, assignee_id: UUID, actor_id: UUID | None = None) -> dict[str, Any]:
        payload = {
            "investigation_id": str(investigation_id),
            "assignee_id": str(assignee_id),
            "actor_id": str(actor_id) if actor_id else None,
        }
        await event_service.emit_event(EventType.INVESTIGATION_ASSIGNED, str(organization_id), payload)
        await notification_service.send_collaboration_notification(
            str(organization_id),
            f"Assignment updated for investigation {investigation_id}",
            payload,
        )
        return payload

    async def upload_investigation_evidence(
        self,
        organization_id: UUID,
        investigation_id: UUID,
        file_path: str,
        description: str,
        uploaded_by_id: UUID,
        evidence_type: str = "note",
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        investigation = await self.investigations.get_investigation(investigation_id, str(organization_id))
        if not investigation:
            raise ValueError("investigation not found")
        return await upload_evidence(
            self.db,
            investigation_id=investigation_id,
            file_path=file_path,
            description=description,
            uploaded_by=uploaded_by_id,
            evidence_type=evidence_type,
            metadata=metadata,
        )

    async def attach_investigation_evidence(
        self,
        organization_id: UUID,
        investigation_id: UUID,
        evidence_id: UUID,
        description: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        investigation = await self.investigations.get_investigation(investigation_id, str(organization_id))
        if not investigation:
            raise ValueError("investigation not found")
        return await attach_evidence(self.db, investigation_id=investigation_id, evidence_id=evidence_id, description=description, metadata=metadata)
