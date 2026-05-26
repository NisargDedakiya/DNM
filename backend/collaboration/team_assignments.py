"""
Team assignment helpers for shared investigations.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.events import EventType
from backend.models.investigation import Investigation
from backend.models.task_assignment import TaskAssignment
from backend.services.event_service import event_service


async def assign_investigation(
    db: AsyncSession,
    investigation_id: UUID,
    assignee_id: UUID,
    assigned_by: UUID | None = None,
    status: str = "assigned",
    escalation_level: str | None = None,
    escalation_reason: str | None = None,
) -> dict[str, Any]:
    """Assign ownership of an investigation to an analyst."""
    investigation = await db.get(Investigation, investigation_id)
    if not investigation:
        raise ValueError("investigation not found")

    assignment = TaskAssignment(
        investigation_id=investigation_id,
        assignee_id=assignee_id,
        status=status,
        assigned_at=datetime.now(timezone.utc).isoformat(),
        assigned_by=assigned_by,
        escalation_level=escalation_level,
        escalation_reason=escalation_reason,
    )
    investigation.assigned_to = assignee_id
    investigation.status = "triaging" if investigation.status == "open" else investigation.status
    investigation.workflow_stage = "triaging" if investigation.workflow_stage == "open" else investigation.workflow_stage

    db.add(assignment)
    await db.flush()

    payload = {
        "investigation_id": str(investigation_id),
        "assignment_id": str(assignment.id),
        "assignee_id": str(assignee_id),
        "assigned_by": str(assigned_by) if assigned_by else None,
        "status": status,
        "escalation_level": escalation_level,
        "escalation_reason": escalation_reason,
    }
    await event_service.emit_event(EventType.INVESTIGATION_ASSIGNED, str(investigation.organization_id), payload)
    return payload


async def reassign_task(
    db: AsyncSession,
    investigation_id: UUID,
    new_assignee_id: UUID,
    assigned_by: UUID | None = None,
    escalation_reason: str | None = None,
) -> dict[str, Any]:
    """Reassign an investigation to another analyst with escalation history."""
    current = await db.execute(
        select(TaskAssignment).where(TaskAssignment.investigation_id == investigation_id).order_by(TaskAssignment.created_at.desc()).limit(1)
    )
    previous = current.scalar_one_or_none()
    if previous:
        previous.status = "reassigned"

    result = await assign_investigation(
        db,
        investigation_id=investigation_id,
        assignee_id=new_assignee_id,
        assigned_by=assigned_by,
        status="reassigned",
        escalation_level="escalated" if escalation_reason else None,
        escalation_reason=escalation_reason,
    )
    investigation = await db.get(Investigation, investigation_id)
    if investigation:
        await event_service.emit_event(EventType.INVESTIGATION_REASSIGNED, str(investigation.organization_id), result)
    return result


async def track_assignment_status(db: AsyncSession, investigation_id: UUID) -> dict[str, Any]:
    """Return the current and historical assignment state for an investigation."""
    result = await db.execute(
        select(TaskAssignment).where(TaskAssignment.investigation_id == investigation_id).order_by(TaskAssignment.created_at.asc())
    )
    assignments = result.scalars().all()
    return {
        "investigation_id": str(investigation_id),
        "current": {
            "assignee_id": str(assignments[-1].assignee_id) if assignments else None,
            "status": assignments[-1].status if assignments else None,
            "assigned_at": assignments[-1].assigned_at if assignments else None,
        },
        "history": [
            {
                "id": str(item.id),
                "assignee_id": str(item.assignee_id),
                "status": item.status,
                "assigned_at": item.assigned_at,
                "assigned_by": str(item.assigned_by) if item.assigned_by else None,
                "escalation_level": item.escalation_level,
                "escalation_reason": item.escalation_reason,
            }
            for item in assignments
        ],
    }
