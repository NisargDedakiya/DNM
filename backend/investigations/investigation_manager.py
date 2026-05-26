"""
Investigation lifecycle manager.
"""
from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.investigation import Investigation


INVESTIGATION_STATES = ("open", "triaging", "validating", "reporting", "resolved")


class InvestigationManager:
    """Creates and manages collaboration investigations."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_investigation(
        self,
        organization_id: str,
        title: str,
        severity: str = "medium",
        status: str = "open",
        assigned_to: UUID | None = None,
        source_finding_id: UUID | None = None,
        summary: str | None = None,
    ) -> Investigation:
        if status not in INVESTIGATION_STATES:
            raise ValueError(f"invalid investigation status: {status}")

        investigation = Investigation(
            organization_id=str(organization_id),
            title=title,
            severity=severity,
            status=status,
            assigned_to=assigned_to,
            source_finding_id=source_finding_id,
            summary=summary,
            workflow_stage=status,
        )
        self.db.add(investigation)
        await self.db.flush()
        return investigation

    async def get_investigation(self, investigation_id: UUID, organization_id: str) -> Investigation | None:
        investigation = await self.db.get(Investigation, investigation_id)
        if not investigation:
            return None
        if str(investigation.organization_id) != str(organization_id):
            return None
        return investigation

    async def list_investigations(
        self,
        organization_id: str,
        status: str | None = None,
        severity: str | None = None,
        limit: int = 100,
    ) -> list[Investigation]:
        query = select(Investigation).where(Investigation.organization_id == str(organization_id))
        if status:
            query = query.where(Investigation.status == status)
        if severity:
            query = query.where(Investigation.severity == severity)
        query = query.order_by(Investigation.created_at.desc()).limit(limit)
        result = await self.db.execute(query)
        return result.scalars().all()

    async def update_status(self, investigation_id: UUID, organization_id: str, status: str) -> Investigation:
        if status not in INVESTIGATION_STATES:
            raise ValueError(f"invalid investigation status: {status}")
        investigation = await self.get_investigation(investigation_id, organization_id)
        if not investigation:
            raise ValueError("investigation not found")
        investigation.status = status
        investigation.workflow_stage = status
        await self.db.flush()
        return investigation

    async def resolve_investigation(self, investigation_id: UUID, organization_id: str, resolution_summary: str | None = None) -> Investigation:
        investigation = await self.update_status(investigation_id, organization_id, "resolved")
        investigation.summary = resolution_summary or investigation.summary
        return investigation
