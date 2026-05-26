"""
Investigation workflow tracking and notifications.
"""
from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.events import EventType
from backend.investigations.investigation_manager import InvestigationManager, INVESTIGATION_STATES
from backend.services.event_service import event_service
from backend.services.notification_service import notification_service


STAGE_PROGRESS = {
    "open": 0,
    "triaging": 20,
    "validating": 50,
    "reporting": 80,
    "resolved": 100,
}


class WorkflowTracker:
    """Tracks status transitions for collaborative investigations."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.investigations = InvestigationManager(db)

    async def update_workflow_stage(
        self,
        organization_id: str,
        investigation_id: UUID,
        stage: str,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        investigation = await self.investigations.update_status(investigation_id, organization_id, stage)
        payload = {
            "investigation_id": str(investigation_id),
            "organization_id": str(organization_id),
            "stage": stage,
            "progress": STAGE_PROGRESS.get(stage, 0),
            "metadata": metadata or {},
        }
        await event_service.emit_event(EventType.INVESTIGATION_WORKFLOW_UPDATED, str(organization_id), payload)
        await notification_service.send_collaboration_notification(str(organization_id), f"Investigation moved to {stage}", payload)
        return payload

    async def track_resolution_progress(self, organization_id: str, investigation_id: UUID) -> dict[str, Any]:
        investigation = await self.investigations.get_investigation(investigation_id, organization_id)
        if not investigation:
            raise ValueError("investigation not found")
        progress = STAGE_PROGRESS.get(investigation.workflow_stage or investigation.status, 0)
        return {
            "investigation_id": str(investigation_id),
            "status": investigation.status,
            "workflow_stage": investigation.workflow_stage,
            "progress": progress,
            "is_complete": progress >= 100,
        }

    async def notify_workflow_changes(self, organization_id: str, investigation_id: UUID, message: str, metadata: dict[str, Any] | None = None) -> dict[str, Any]:
        payload = {
            "investigation_id": str(investigation_id),
            "message": message,
            "metadata": metadata or {},
        }
        await event_service.emit_event(EventType.INVESTIGATION_WORKFLOW_UPDATED, str(organization_id), payload)
        await notification_service.send_collaboration_notification(str(organization_id), message, payload)
        return payload
