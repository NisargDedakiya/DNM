"""
Asset priority service.

Calculates exposure-aware priority scores, ranks recon targets,
and identifies high-value assets for focused security attention.
Risk-based prioritization using multi-factor scoring.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.asset import Asset
from backend.models.exposure import Exposure
from backend.models.finding import Finding

logger = logging.getLogger(__name__)

# Priority scoring weights
_RISK_SCORE_WEIGHT = 0.40
_EXPOSURE_COUNT_WEIGHT = 0.25
_INTERNET_FACING_WEIGHT = 0.20
_FINDING_COUNT_WEIGHT = 0.10
_RECENCY_WEIGHT = 0.05

# Exposure severity scores
_SEVERITY_SCORES = {
    "critical": 10.0,
    "high": 7.5,
    "medium": 5.0,
    "low": 2.5,
    "info": 1.0,
}

# Asset type multipliers
_ASSET_TYPE_MULTIPLIER = {
    "web_application": 1.3,
    "api": 1.4,
    "admin_panel": 1.6,
    "database": 1.5,
    "cms": 1.2,
    "cdn": 0.8,
    "static_site": 0.7,
    "unknown": 1.0,
}


class AssetPriorityService:
    """
    Exposure-aware asset priority scoring and ranking.

    Scores assets based on risk score, exposure count, internet-facing
    status, finding history, and recon recency. Identifies high-value
    targets for focused recon effort.
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def calculate_asset_priority(
        self,
        asset_id: UUID,
    ) -> Dict[str, Any]:
        """
        Calculate multi-factor priority score for a single asset.

        Args:
            asset_id: Asset to score

        Returns:
            dict: {
                asset_id, priority_score (0-100), priority_level,
                factors, recommended_recon_depth, score_breakdown
            }
        """
        result = await self.db.execute(select(Asset).where(Asset.id == asset_id))
        asset = result.scalars().first()
        if not asset:
            return {"asset_id": str(asset_id), "priority_score": 0.0, "priority_level": "unknown"}

        # Exposures for this asset
        exp_result = await self.db.execute(
            select(Exposure).where(
                and_(Exposure.asset_id == asset_id, Exposure.is_active == True)
            )
        )
        exposures = exp_result.scalars().all()

        # Findings scoped to the asset's program (Finding has no asset_id column)
        program_id = getattr(asset, "program_id", None)
        if program_id is not None:
            finding_result = await self.db.execute(
                select(func.count(Finding.id)).where(Finding.program_id == program_id)
            )
        else:
            finding_result = await self.db.execute(
                select(func.count(Finding.id)).where(Finding.id == None)  # noqa: E711
            )
        finding_count = finding_result.scalar() or 0

        # ── Score components ──────────────────────────────────
        risk_score = float(getattr(asset, "risk_score", 0.0) or 0.0)
        risk_component = (risk_score / 100.0) * _RISK_SCORE_WEIGHT * 100

        exposure_score = sum(
            _SEVERITY_SCORES.get(e.risk_level, 5.0) for e in exposures
        )
        exposure_norm = min(100.0, exposure_score * 2.0)
        exposure_component = (exposure_norm / 100.0) * _EXPOSURE_COUNT_WEIGHT * 100

        is_internet = bool(getattr(asset, "is_internet_facing", False))
        internet_component = _INTERNET_FACING_WEIGHT * 100 if is_internet else 0.0

        finding_norm = min(100.0, finding_count * 5.0)
        finding_component = (finding_norm / 100.0) * _FINDING_COUNT_WEIGHT * 100

        last_seen = getattr(asset, "last_seen", None)
        if last_seen:
            days_ago = (datetime.utcnow() - last_seen).days
            recency_norm = max(0.0, 1.0 - (days_ago / 30.0))
        else:
            recency_norm = 0.5
        recency_component = recency_norm * _RECENCY_WEIGHT * 100

        raw_score = (
            risk_component + exposure_component +
            internet_component + finding_component + recency_component
        )

        # Apply asset type multiplier
        asset_type = getattr(asset, "asset_type", "unknown") or "unknown"
        multiplier = _ASSET_TYPE_MULTIPLIER.get(asset_type, 1.0)
        final_score = min(100.0, raw_score * multiplier)

        priority_level = self._score_to_priority(final_score)
        recon_depth = self._priority_to_recon_depth(priority_level)

        return {
            "asset_id": str(asset_id),
            "hostname": getattr(asset, "hostname", ""),
            "priority_score": round(final_score, 2),
            "priority_level": priority_level,
            "recommended_recon_depth": recon_depth,
            "score_breakdown": {
                "risk_component": round(risk_component, 2),
                "exposure_component": round(exposure_component, 2),
                "internet_facing_component": round(internet_component, 2),
                "finding_component": round(finding_component, 2),
                "recency_component": round(recency_component, 2),
                "asset_type_multiplier": multiplier,
            },
            "factors": {
                "risk_score": risk_score,
                "active_exposures": len(exposures),
                "total_findings": finding_count,
                "is_internet_facing": is_internet,
                "asset_type": asset_type,
            },
            "scored_at": datetime.utcnow().isoformat(),
        }

    async def rank_recon_targets(
        self,
        organization_id: UUID,
        program_id: Optional[UUID] = None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """
        Rank all assets by recon priority score.

        Args:
            organization_id: Organization ID
            program_id: Optional program scope filter
            limit: Maximum results

        Returns:
            list: Assets ranked by priority score (highest first)
        """
        query = select(Asset)
        if program_id:
            query = query.where(Asset.program_id == program_id)

        result = await self.db.execute(query)
        assets = result.scalars().all()

        scored: List[Dict[str, Any]] = []
        for asset in assets:
            score_data = await self.calculate_asset_priority(asset.id)
            scored.append(score_data)

        scored.sort(key=lambda x: x.get("priority_score", 0.0), reverse=True)
        ranked = []
        for rank, item in enumerate(scored[:limit], 1):
            item["rank"] = rank
            ranked.append(item)

        return ranked

    async def identify_high_value_assets(
        self,
        organization_id: UUID,
        program_id: Optional[UUID] = None,
        min_priority_level: str = "high",
    ) -> Dict[str, Any]:
        """
        Identify and categorize high-value assets for recon focus.

        Args:
            organization_id: Organization ID
            program_id: Optional program filter
            min_priority_level: Minimum priority level to include

        Returns:
            dict: {
                high_value_assets, summary_stats,
                attack_surface_concentration, recon_gaps
            }
        """
        ranked = await self.rank_recon_targets(organization_id, program_id, limit=100)

        priority_order = ["critical", "high", "medium", "low", "info"]
        min_idx = priority_order.index(min_priority_level) if min_priority_level in priority_order else 1

        filtered = [
            a for a in ranked
            if priority_order.index(a.get("priority_level", "info")) <= min_idx
        ]

        critical = [a for a in ranked if a.get("priority_level") == "critical"]
        high = [a for a in ranked if a.get("priority_level") == "high"]
        medium = [a for a in ranked if a.get("priority_level") == "medium"]

        internet_facing = [a for a in filtered if a.get("factors", {}).get("is_internet_facing")]
        recon_gaps = [
            a for a in ranked
            if a.get("factors", {}).get("active_exposures", 0) == 0
            and a.get("priority_score", 0) < 20
        ]

        return {
            "high_value_assets": filtered[:20],
            "summary_stats": {
                "total_assets_scored": len(ranked),
                "critical_priority": len(critical),
                "high_priority": len(high),
                "medium_priority": len(medium),
                "internet_facing_high_value": len(internet_facing),
                "recon_gap_assets": len(recon_gaps),
            },
            "attack_surface_concentration": {
                "top_3_assets": [
                    {"rank": a["rank"], "hostname": a.get("hostname"), "score": a["priority_score"]}
                    for a in ranked[:3]
                ],
                "concentration_note": (
                    "Top assets represent highest recon opportunity — prioritize accordingly"
                ),
            },
            "recon_gaps": [
                {"hostname": a.get("hostname"), "reason": "low_coverage_high_potential"}
                for a in recon_gaps[:10]
            ],
            "generated_at": datetime.utcnow().isoformat(),
            "advisory_note": "High-value asset identification is advisory. Human review required.",
        }

    async def get_priority_trend(
        self,
        asset_id: UUID,
        days: int = 30,
    ) -> Dict[str, Any]:
        """
        Get priority score trend analysis for an asset.

        Args:
            asset_id: Asset to analyze
            days: Historical window in days

        Returns:
            dict: Trend data with current score and change indicators
        """
        current = await self.calculate_asset_priority(asset_id)

        # Snapshot comparison based on exposure changes
        exp_result = await self.db.execute(
            select(Exposure).where(Exposure.asset_id == asset_id)
        )
        all_exposures = exp_result.scalars().all()

        since = datetime.utcnow() - timedelta(days=days)
        new_exposures = sum(
            1 for e in all_exposures
            if e.first_detected and e.first_detected >= since
        )
        resolved_exposures = sum(
            1 for e in all_exposures
            if not e.is_active and e.updated_at and e.updated_at >= since
        )

        trend_indicator = "stable"
        if new_exposures > resolved_exposures:
            trend_indicator = "increasing_risk"
        elif resolved_exposures > new_exposures:
            trend_indicator = "decreasing_risk"

        return {
            "asset_id": str(asset_id),
            "current_score": current.get("priority_score", 0.0),
            "current_level": current.get("priority_level", "unknown"),
            "trend_period_days": days,
            "new_exposures_period": new_exposures,
            "resolved_exposures_period": resolved_exposures,
            "trend_indicator": trend_indicator,
            "score_factors": current.get("score_breakdown", {}),
            "analyzed_at": datetime.utcnow().isoformat(),
        }

    @staticmethod
    def _score_to_priority(score: float) -> str:
        if score >= 80:
            return "critical"
        elif score >= 60:
            return "high"
        elif score >= 40:
            return "medium"
        elif score >= 20:
            return "low"
        return "info"

    @staticmethod
    def _priority_to_recon_depth(priority: str) -> str:
        return {
            "critical": "full_depth",
            "high": "deep",
            "medium": "standard",
            "low": "surface",
            "info": "passive_only",
        }.get(priority, "standard")
