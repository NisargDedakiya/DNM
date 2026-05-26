"""
Continuous exposure monitoring orchestration.
"""
from __future__ import annotations

import asyncio
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.events import EventType
from backend.services.event_service import event_service
from backend.services.exposure_service import ExposureService


class ContinuousMonitor:
    """Coordinates repeated exposure validation in a scheduler-safe way."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.exposure_service = ExposureService(db)

    async def start_monitoring(
        self,
        organization_id: UUID,
        assets: list[str] | None = None,
        interval_seconds: int = 300,
        cycles: int = 1,
    ) -> dict[str, Any]:
        targets = assets or ["__organization__"]
        runs: list[dict[str, Any]] = []
        for _ in range(max(1, cycles)):
            for asset in targets:
                runs.append(await self.monitor_target(organization_id, asset))
            if cycles > 1:
                await asyncio.sleep(max(1, interval_seconds))
        return {
            "organization_id": str(organization_id),
            "targets": targets,
            "cycles": cycles,
            "results": runs,
        }

    async def monitor_target(self, organization_id: UUID, asset: str) -> dict[str, Any]:
        analysis = await self.exposure_service.analyze_exposure_evolution(organization_id, asset=asset)
        await event_service.emit_event(
            EventType.EXPOSURE_SNAPSHOT,
            str(organization_id),
            {
                "asset": asset,
                "summary": analysis.get("summary", {}),
                "risk_score": analysis.get("snapshot", {}).get("risk_score", 0.0),
            },
        )
        return analysis

    async def schedule_exposure_checks(
        self,
        organization_id: UUID,
        assets: list[str],
        high_risk_only: bool = False,
    ) -> list[dict[str, Any]]:
        schedule: list[dict[str, Any]] = []
        for asset in assets:
            risk_summary = await self.exposure_service.generate_exposure_summary(organization_id, asset=asset)
            if high_risk_only and risk_summary.get("overall_risk_score", 0.0) < 7:
                continue
            schedule.append(
                {
                    "asset": asset,
                    "organization_id": str(organization_id),
                    "next_check_in_seconds": 300 if risk_summary.get("overall_risk_score", 0.0) >= 7 else 900,
                    "risk_score": risk_summary.get("overall_risk_score", 0.0),
                }
            )
        return schedule

