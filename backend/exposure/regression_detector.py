"""
Detect recurring risky exposure states and regressions.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from backend.exposure.exposure_tracker import ExposureTracker, HIGH_SIGNAL_KEYWORDS


class RegressionDetector:
    """Recurring exposure and vulnerability regression analysis."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.tracker = ExposureTracker(db)

    async def detect_regressions(
        self,
        organization_id: UUID,
        asset: str | None = None,
        limit: int = 10,
    ) -> dict[str, Any]:
        snapshots = await self.tracker.get_recent_snapshots(organization_id, asset=asset, limit=max(limit, 2))
        if len(snapshots) < 2:
            return {
                "organization_id": str(organization_id),
                "asset": asset,
                "regressions": [],
                "repeat_exposures": [],
                "recurring_patterns": [],
            }

        latest_state = snapshots[0].exposure_state
        prior_states = [snapshot.exposure_state for snapshot in snapshots[1:]]
        repeat_exposures = self.identify_repeat_exposure(prior_states + [latest_state])
        recurring_patterns = self.analyze_recurring_patterns(prior_states + [latest_state])

        regressions = []
        for key, current_item in latest_state.items():
            for previous_state in prior_states:
                if key in previous_state and previous_state[key] != current_item:
                    regressions.append(
                        {
                            "key": key,
                            "previous": previous_state[key],
                            "current": current_item,
                        }
                    )

        return {
            "organization_id": str(organization_id),
            "asset": asset,
            "regressions": regressions,
            "repeat_exposures": repeat_exposures,
            "recurring_patterns": recurring_patterns,
            "regression_count": len(regressions),
        }

    def identify_repeat_exposure(self, exposure_states: list[dict[str, Any]]) -> list[dict[str, Any]]:
        counter = Counter()
        examples: dict[str, dict[str, Any]] = {}
        for state in exposure_states:
            for key, item in state.items():
                signature = f"{item.get('asset_id')}:{item.get('exposure_type')}:{item.get('risk_level')}:{item.get('title')}"
                counter[signature] += 1
                examples.setdefault(signature, item)

        return [
            {
                "signature": signature,
                "count": count,
                "example": examples[signature],
            }
            for signature, count in counter.most_common()
            if count > 1
        ]

    def analyze_recurring_patterns(self, exposure_states: list[dict[str, Any]]) -> list[dict[str, Any]]:
        pattern_counter = Counter()
        for state in exposure_states:
            for item in state.values():
                text_blob = " ".join(str(item.get(field, "")).lower() for field in ("title", "exposure_type", "risk_level"))
                for keyword in HIGH_SIGNAL_KEYWORDS:
                    if keyword in text_blob:
                        pattern_counter[keyword] += 1

        return [
            {"pattern": pattern, "count": count}
            for pattern, count in pattern_counter.most_common()
            if count > 1
        ]

