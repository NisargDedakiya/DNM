"""
Track exposure state changes and create org-isolated snapshots.
"""
from __future__ import annotations

from datetime import datetime
from statistics import mean
from typing import Any
from uuid import UUID

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.exposure import Exposure
from backend.models.exposure_snapshot import ExposureSnapshot


HIGH_SIGNAL_KEYWORDS = ("auth", "graphql", "cloud", "admin", "oauth", "upload", "ssrf")


def _safe_text(value: Any) -> str:
    return " ".join(str(value or "").split())[:255]


class ExposureTracker:
    """Builds exposure snapshots and diffs them safely within an org."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_exposure_snapshot(
        self,
        organization_id: UUID,
        asset: str | None = None,
        limit: int = 200,
    ) -> ExposureSnapshot:
        exposures = await self._load_exposures(organization_id, asset=asset, limit=limit)
        exposure_state = self._build_exposure_state(exposures)
        risk_score = round(mean(item["risk_score"] for item in exposure_state.values()) if exposure_state else 0.0, 2)

        snapshot = ExposureSnapshot(
            organization_id=organization_id,
            asset=_safe_text(asset or "__organization__"),
            exposure_state=exposure_state,
            risk_score=risk_score,
        )
        self.db.add(snapshot)
        await self.db.flush()
        return snapshot

    async def get_latest_snapshot(
        self,
        organization_id: UUID,
        asset: str | None = None,
    ) -> ExposureSnapshot | None:
        query = select(ExposureSnapshot).where(ExposureSnapshot.organization_id == organization_id)
        if asset:
            query = query.where(ExposureSnapshot.asset == _safe_text(asset))
        query = query.order_by(desc(ExposureSnapshot.created_at)).limit(1)
        result = await self.db.execute(query)
        return result.scalars().first()

    async def get_recent_snapshots(
        self,
        organization_id: UUID,
        asset: str | None = None,
        limit: int = 10,
    ) -> list[ExposureSnapshot]:
        query = select(ExposureSnapshot).where(ExposureSnapshot.organization_id == organization_id)
        if asset:
            query = query.where(ExposureSnapshot.asset == _safe_text(asset))
        query = query.order_by(desc(ExposureSnapshot.created_at)).limit(limit)
        result = await self.db.execute(query)
        return result.scalars().all()

    def compare_exposure_states(
        self,
        previous_state: dict[str, Any] | None,
        current_state: dict[str, Any] | None,
    ) -> dict[str, Any]:
        previous_state = previous_state or {}
        current_state = current_state or {}

        previous_keys = set(previous_state)
        current_keys = set(current_state)

        added_keys = current_keys - previous_keys
        removed_keys = previous_keys - current_keys
        shared_keys = previous_keys & current_keys

        changed_items = []
        for key in shared_keys:
            previous_item = previous_state[key]
            current_item = current_state[key]
            if previous_item != current_item:
                changed_items.append(
                    {
                        "key": key,
                        "previous": previous_item,
                        "current": current_item,
                    }
                )

        return {
            "added": [current_state[key] for key in added_keys],
            "removed": [previous_state[key] for key in removed_keys],
            "changed": changed_items,
            "summary": {
                "added_count": len(added_keys),
                "removed_count": len(removed_keys),
                "changed_count": len(changed_items),
            },
        }

    def detect_new_exposures(
        self,
        previous_state: dict[str, Any] | None,
        current_state: dict[str, Any] | None,
    ) -> list[dict[str, Any]]:
        comparison = self.compare_exposure_states(previous_state, current_state)
        return comparison["added"]

    async def _load_exposures(
        self,
        organization_id: UUID,
        asset: str | None = None,
        limit: int = 200,
    ) -> list[Exposure]:
        query = select(Exposure).where(Exposure.organization_id == organization_id)
        if asset:
            query = query.where(Exposure.asset.has(hostname=_safe_text(asset)))
        query = query.order_by(desc(Exposure.risk_score)).limit(limit)
        result = await self.db.execute(query)
        return result.scalars().all()

    def _build_exposure_state(self, exposures: list[Exposure]) -> dict[str, Any]:
        state: dict[str, Any] = {}
        for exposure in exposures:
            key = f"{exposure.asset_id}:{exposure.exposure_type}:{_safe_text(exposure.title)}"
            state[key] = {
                "key": key,
                "asset_id": str(exposure.asset_id),
                "title": _safe_text(exposure.title),
                "exposure_type": str(exposure.exposure_type),
                "risk_level": str(exposure.risk_level),
                "risk_score": float(exposure.risk_score or 0.0),
                "confidence_score": float(exposure.confidence_score or 0.0),
                "is_active": bool(exposure.is_active),
                "first_detected": exposure.first_detected.isoformat() if exposure.first_detected else None,
                "last_detected": exposure.last_detected.isoformat() if exposure.last_detected else None,
            }
        return state

