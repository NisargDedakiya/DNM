"""
Exposure history intelligence for asset drift and auth evolution.
"""
from __future__ import annotations

from collections import Counter
from typing import Any
from uuid import UUID

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.exposure_event import ExposureEvent


class ExposureHistory:
    """Organization-isolated exposure event tracker."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def record_exposure_event(
        self,
        organization_id: UUID,
        asset: str,
        event_type: str,
        severity: str,
    ) -> ExposureEvent:
        event = ExposureEvent(
            organization_id=organization_id,
            asset=" ".join(asset.split())[:255],
            event_type=" ".join(event_type.split())[:64].lower(),
            severity=" ".join(severity.split())[:32].lower(),
        )
        self.db.add(event)
        await self.db.flush()
        return event

    async def detect_exposure_patterns(
        self,
        organization_id: UUID,
        limit: int = 50,
    ) -> dict[str, Any]:
        stmt = (
            select(ExposureEvent)
            .where(ExposureEvent.organization_id == organization_id)
            .order_by(desc(ExposureEvent.created_at))
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        events = result.scalars().all()

        event_type_counts = Counter(event.event_type for event in events)
        severity_counts = Counter(event.severity for event in events)
        asset_counts = Counter(event.asset for event in events)

        return {
            "organization_id": str(organization_id),
            "total_events": len(events),
            "event_type_counts": dict(event_type_counts),
            "severity_counts": dict(severity_counts),
            "top_assets": [
                {"asset": asset, "count": count}
                for asset, count in asset_counts.most_common(10)
            ],
        }

    async def analyze_asset_evolution(
        self,
        organization_id: UUID,
        asset: str,
        limit: int = 20,
    ) -> dict[str, Any]:
        stmt = (
            select(ExposureEvent)
            .where(
                ExposureEvent.organization_id == organization_id,
                ExposureEvent.asset == asset,
            )
            .order_by(desc(ExposureEvent.created_at))
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        events = result.scalars().all()

        return {
            "organization_id": str(organization_id),
            "asset": asset,
            "event_count": len(events),
            "events": [
                {
                    "id": str(event.id),
                    "event_type": event.event_type,
                    "severity": event.severity,
                    "created_at": event.created_at.isoformat(),
                }
                for event in events
            ],
        }

