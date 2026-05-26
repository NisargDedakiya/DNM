"""
Watch high-risk assets and publish exposure change notifications.
"""
from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.events import EventType
from backend.services.event_service import event_service
from backend.services.exposure_service import ExposureService


class AssetWatchdog:
    """Asset-scoped exposure watchdog with org isolation."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.exposure_service = ExposureService(db)

    async def watch_asset(self, organization_id: UUID, asset: str) -> dict[str, Any]:
        change = await self.detect_asset_change(organization_id, asset)
        await self.notify_exposure_change(organization_id, asset, change)
        return change

    async def detect_asset_change(self, organization_id: UUID, asset: str) -> dict[str, Any]:
        analysis = await self.exposure_service.analyze_exposure_evolution(organization_id, asset=asset)
        return {
            "organization_id": str(organization_id),
            "asset": asset,
            "drift": analysis.get("drift", {}),
            "risk_evolution": analysis.get("risk_evolution", {}),
            "regressions": analysis.get("regressions", {}),
            "summary": analysis.get("summary", {}),
        }

    async def notify_exposure_change(self, organization_id: UUID, asset: str, change: dict[str, Any]) -> None:
        await event_service.emit_event(
            EventType.EXPOSURE_DRIFT,
            str(organization_id),
            {
                "asset": asset,
                "change": change,
            },
        )

