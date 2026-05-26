"""
Detect exposure drift, auth change mutations, and risky deltas.
"""
from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from backend.exposure.exposure_tracker import ExposureTracker, HIGH_SIGNAL_KEYWORDS
from backend.models.drift_event import DriftEvent


class DriftDetector:
    """Risk-aware drift analysis for exposures and auth surfaces."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.tracker = ExposureTracker(db)

    async def detect_asset_drift(
        self,
        organization_id: UUID,
        asset: str | None = None,
        limit: int = 200,
    ) -> dict[str, Any]:
        snapshots = await self.tracker.get_recent_snapshots(organization_id, asset=asset, limit=2)
        if len(snapshots) < 2:
            return {
                "organization_id": str(organization_id),
                "asset": asset,
                "drift_detected": False,
                "changes": {"added": [], "removed": [], "changed": []},
                "severity": "info",
            }

        current_snapshot = snapshots[0]
        previous_snapshot = snapshots[1]
        changes = self.tracker.compare_exposure_states(previous_snapshot.exposure_state, current_snapshot.exposure_state)
        severity = self.analyze_drift_risk(changes)
        high_risk_changes = self.identify_high_risk_changes(changes)

        if high_risk_changes:
            await self._persist_drift_event(organization_id, asset or current_snapshot.asset, severity, high_risk_changes)

        return {
            "organization_id": str(organization_id),
            "asset": asset or current_snapshot.asset,
            "drift_detected": bool(changes["summary"]["added_count"] or changes["summary"]["removed_count"] or changes["summary"]["changed_count"]),
            "changes": changes,
            "severity": severity,
            "high_risk_changes": high_risk_changes,
            "previous_snapshot": str(previous_snapshot.id),
            "current_snapshot": str(current_snapshot.id),
        }

    def analyze_drift_risk(self, changes: dict[str, Any]) -> str:
        changed_count = int(changes.get("summary", {}).get("changed_count", 0))
        added_count = int(changes.get("summary", {}).get("added_count", 0))
        removed_count = int(changes.get("summary", {}).get("removed_count", 0))

        risk_markers = 0
        for item in changes.get("added", []) + changes.get("removed", []):
            text_blob = " ".join(str(item.get(field, "")).lower() for field in ("title", "exposure_type", "risk_level"))
            if any(keyword in text_blob for keyword in HIGH_SIGNAL_KEYWORDS):
                risk_markers += 1

        score = added_count + removed_count + changed_count + risk_markers * 2
        if score >= 8:
            return "critical"
        if score >= 5:
            return "high"
        if score >= 2:
            return "medium"
        return "low"

    def identify_high_risk_changes(self, changes: dict[str, Any]) -> list[dict[str, Any]]:
        high_risk_changes: list[dict[str, Any]] = []
        for bucket_name in ("added", "removed"):
            for item in changes.get(bucket_name, []):
                text_blob = " ".join(str(item.get(field, "")).lower() for field in ("title", "exposure_type", "risk_level"))
                if any(keyword in text_blob for keyword in HIGH_SIGNAL_KEYWORDS):
                    high_risk_changes.append({"bucket": bucket_name, **item})
        for item in changes.get("changed", []):
            current_blob = " ".join(str(item.get("current", {}).get(field, "")).lower() for field in ("title", "exposure_type", "risk_level"))
            previous_blob = " ".join(str(item.get("previous", {}).get(field, "")).lower() for field in ("title", "exposure_type", "risk_level"))
            if any(keyword in current_blob or keyword in previous_blob for keyword in HIGH_SIGNAL_KEYWORDS):
                high_risk_changes.append({"bucket": "changed", **item})
        return high_risk_changes

    async def _persist_drift_event(
        self,
        organization_id: UUID,
        asset: str,
        severity: str,
        high_risk_changes: list[dict[str, Any]],
    ) -> DriftEvent:
        event = DriftEvent(
            organization_id=organization_id,
            asset=asset,
            drift_type="exposure_drift",
            severity=severity,
            summary=f"{len(high_risk_changes)} high-risk exposure changes detected",
        )
        self.db.add(event)
        await self.db.flush()
        return event

