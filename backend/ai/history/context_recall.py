"""
Contextual recall helpers for historical intelligence retrieval.
"""
from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import desc, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.ai.history.hunt_memory_engine import HuntMemoryEngine
from backend.models.exposure_event import ExposureEvent
from backend.models.finding import Finding


class ContextRecall:
    """Prioritized historical recall for hunt-time AI reasoning."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.memory_engine = HuntMemoryEngine(db)

    async def recall_similar_findings(
        self,
        organization_id: UUID,
        query: str,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        tokens = [token for token in query.lower().split() if len(token) > 2]
        stmt = select(Finding).where(Finding.organization_id == organization_id)
        if tokens:
            filters = [Finding.title.ilike(f"%{token}%") | Finding.description.ilike(f"%{token}%") for token in tokens[:6]]
            stmt = stmt.where(or_(*filters) if len(filters) > 1 else filters[0])
        stmt = stmt.order_by(desc(Finding.created_at)).limit(limit)

        result = await self.db.execute(stmt)
        findings = result.scalars().all()

        return [
            {
                "id": str(finding.id),
                "title": finding.title,
                "severity": str(finding.severity),
                "status": str(finding.status),
                "endpoint": finding.endpoint,
                "created_at": finding.created_at.isoformat(),
            }
            for finding in findings
        ]

    async def recall_attack_paths(
        self,
        organization_id: UUID,
        query: str,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        return await self.memory_engine.retrieve_related_memory(
            organization_id=organization_id,
            query=query,
            memory_type="attack_chain",
            limit=limit,
        )

    async def recall_historical_exposure(
        self,
        organization_id: UUID,
        query: str,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        stmt = select(ExposureEvent).where(ExposureEvent.organization_id == organization_id)
        tokens = [token for token in query.lower().split() if len(token) > 2]
        if tokens:
            token_filters = [ExposureEvent.asset.ilike(f"%{token}%") | ExposureEvent.event_type.ilike(f"%{token}%") for token in tokens[:6]]
            stmt = stmt.where(or_(*token_filters) if len(token_filters) > 1 else token_filters[0])
        stmt = stmt.order_by(desc(ExposureEvent.created_at)).limit(limit)

        result = await self.db.execute(stmt)
        events = result.scalars().all()
        return [
            {
                "id": str(event.id),
                "asset": event.asset,
                "event_type": event.event_type,
                "severity": event.severity,
                "created_at": event.created_at.isoformat(),
            }
            for event in events
        ]

