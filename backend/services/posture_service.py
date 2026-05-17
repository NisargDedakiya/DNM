"""
Posture Service: security posture scoring, trend analysis, and health evaluation.

Provides modular, composable scoring functions that can be consumed by the
executive risk service and reporting engine without coupling them together.

Scoring model
-------------
``calculate_posture_score()`` returns a 0–100 score built from five components:

  Component              Weight   Signal
  ─────────────────────  ──────   ───────────────────────────────────────────
  Exposure severity      35 %     Weighted critical/high/medium/low counts
  Exposure density       20 %     Exposure-to-asset ratio (lower = better)
  Remediation velocity   20 %     % of exposures with active remediation
  Asset coverage         15 %     % of assets that have been scanned recently
  Change momentum        10 %     Net change events in the last 7 days (less = better)

Score bands: CRITICAL(0–30) HIGH(31–50) MEDIUM(51–70) GOOD(71–85) EXCELLENT(86–100)
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import select, and_, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.asset import Asset
from backend.models.exposure import Exposure
from backend.models.change_event import ChangeEvent

logger = logging.getLogger(__name__)

# ── Scoring weights (must sum to 1.0) ────────────────────────────────────────
_W_SEVERITY = 0.35
_W_DENSITY = 0.20
_W_REMEDIATION = 0.20
_W_COVERAGE = 0.15
_W_MOMENTUM = 0.10

# Risk level numeric weights for severity scoring
_SEV_WEIGHT = {"critical": 10.0, "high": 7.0, "medium": 4.0, "low": 1.5, "info": 0.5}

# Posture grade bands
_GRADE_BANDS = [
    (86, "EXCELLENT", "🟢"),
    (71, "GOOD", "🟡"),
    (51, "MEDIUM", "🟠"),
    (31, "HIGH_RISK", "🔴"),
    (0, "CRITICAL", "🚨"),
]


def _score_to_grade(score: float) -> tuple[str, str]:
    """Map a 0-100 score to (grade_label, emoji)."""
    for threshold, label, emoji in _GRADE_BANDS:
        if score >= threshold:
            return label, emoji
    return "CRITICAL", "🚨"


class PostureService:
    """
    Security posture scoring and trend analytics service.

    All methods are workspace-isolated via organization_id.
    Returns plain dicts — no ORM objects — for easy JSON serialisation.
    """

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # =========================================================================
    # POSTURE SCORE
    # =========================================================================

    async def calculate_posture_score(
        self,
        organization_id: UUID,
    ) -> dict[str, Any]:
        """
        Compute a holistic 0–100 security posture score for an organisation.

        Returns
        -------
        dict with:
            score             – composite posture score [0–100]
            grade             – human label (EXCELLENT / GOOD / MEDIUM / HIGH_RISK / CRITICAL)
            grade_emoji       – visual indicator
            components        – breakdown of each scoring component
            posture_summary   – one-line human-readable summary
        """
        components: dict[str, float] = {}

        # ── 1. Severity component ────────────────────────────────────────
        severity_score = await self._score_exposure_severity(organization_id)
        components["exposure_severity"] = round(severity_score, 2)

        # ── 2. Density component ─────────────────────────────────────────
        density_score = await self._score_exposure_density(organization_id)
        components["exposure_density"] = round(density_score, 2)

        # ── 3. Remediation velocity component ────────────────────────────
        remediation_score = await self._score_remediation_velocity(organization_id)
        components["remediation_velocity"] = round(remediation_score, 2)

        # ── 4. Asset coverage component ───────────────────────────────────
        coverage_score = await self._score_asset_coverage(organization_id)
        components["asset_coverage"] = round(coverage_score, 2)

        # ── 5. Change momentum component ──────────────────────────────────
        momentum_score = await self._score_change_momentum(organization_id)
        components["change_momentum"] = round(momentum_score, 2)

        # Composite score (weighted sum)
        composite = (
            severity_score * _W_SEVERITY
            + density_score * _W_DENSITY
            + remediation_score * _W_REMEDIATION
            + coverage_score * _W_COVERAGE
            + momentum_score * _W_MOMENTUM
        )
        composite = round(min(100.0, max(0.0, composite)), 2)

        grade, emoji = _score_to_grade(composite)

        summary = _build_posture_summary(composite, grade, components)

        return {
            "score": composite,
            "grade": grade,
            "grade_emoji": emoji,
            "components": components,
            "posture_summary": summary,
            "calculated_at": datetime.utcnow().isoformat(),
        }

    # =========================================================================
    # RISK TRENDS
    # =========================================================================

    async def analyze_risk_trends(
        self,
        organization_id: UUID,
        days: int = 30,
    ) -> dict[str, Any]:
        """
        Analyse risk change trends over a rolling window.

        Returns daily net-risk-delta, exposure counts, and severity breakdowns
        suitable for trend charts on the executive dashboard.
        """
        since = datetime.utcnow() - timedelta(days=days)

        # Daily change event aggregation
        stmt = (
            select(ChangeEvent)
            .where(
                and_(
                    ChangeEvent.organization_id == organization_id,
                    ChangeEvent.detected_at >= since,
                )
            )
            .order_by(ChangeEvent.detected_at)
        )
        result = await self.db.execute(stmt)
        events = result.scalars().all()

        daily: dict[str, dict[str, Any]] = {}
        for e in events:
            day = e.detected_at.strftime("%Y-%m-%d") if e.detected_at else "unknown"
            if day not in daily:
                daily[day] = {
                    "date": day,
                    "total_events": 0,
                    "net_risk_delta": 0.0,
                    "by_severity": {s: 0 for s in ["critical", "high", "medium", "low", "info"]},
                }
            daily[day]["total_events"] += 1
            sev = e.severity if isinstance(e.severity, str) else e.severity.value
            if sev in daily[day]["by_severity"]:
                daily[day]["by_severity"][sev] += 1

            if e.change_type in ("new_exposure", "new_asset"):
                daily[day]["net_risk_delta"] += e.change_score
            elif e.change_type in ("resolved_exposure", "removed_asset"):
                daily[day]["net_risk_delta"] -= e.change_score

        # Cumulative risk score trajectory
        cumulative = 0.0
        trend_series = []
        for day in sorted(daily.keys()):
            cumulative += daily[day]["net_risk_delta"]
            trend_series.append({
                "date": day,
                "daily_delta": round(daily[day]["net_risk_delta"], 2),
                "cumulative_risk": round(cumulative, 2),
                "total_events": daily[day]["total_events"],
                "severity_breakdown": daily[day]["by_severity"],
            })

        # Week-over-week comparison
        mid_point = datetime.utcnow() - timedelta(days=days // 2)
        first_half = [t for t in trend_series if t["date"] < mid_point.strftime("%Y-%m-%d")]
        second_half = [t for t in trend_series if t["date"] >= mid_point.strftime("%Y-%m-%d")]

        first_total = sum(t["total_events"] for t in first_half)
        second_total = sum(t["total_events"] for t in second_half)
        trend_direction = "improving" if second_total < first_total else ("worsening" if second_total > first_total else "stable")

        return {
            "trend_series": trend_series,
            "total_events": len(events),
            "window_days": days,
            "trend_direction": trend_direction,
            "first_half_events": first_total,
            "second_half_events": second_total,
            "net_risk_change": round(cumulative, 2),
        }

    # =========================================================================
    # EXPOSURE DENSITY
    # =========================================================================

    async def calculate_exposure_density(
        self,
        organization_id: UUID,
    ) -> dict[str, Any]:
        """
        Calculate the exposure-to-asset density ratio.

        Returns density metrics including per-asset exposure count breakdown
        and highest-density assets for targeting.
        """
        asset_count_stmt = select(func.count(Asset.id)).where(
            Asset.organization_id == organization_id
        )
        asset_count = (await self.db.execute(asset_count_stmt)).scalar() or 0

        exposure_stmt = (
            select(Exposure.asset_id, func.count(Exposure.id).label("exp_count"))
            .where(
                and_(
                    Exposure.organization_id == organization_id,
                    Exposure.is_active == True,
                )
            )
            .group_by(Exposure.asset_id)
            .order_by(desc("exp_count"))
        )
        exp_result = await self.db.execute(exposure_stmt)
        per_asset = exp_result.all()

        total_exposures = sum(row[1] for row in per_asset)
        density_ratio = total_exposures / max(asset_count, 1)

        # Density bands
        if density_ratio >= 5:
            density_grade = "CRITICAL"
        elif density_ratio >= 3:
            density_grade = "HIGH"
        elif density_ratio >= 1:
            density_grade = "MEDIUM"
        else:
            density_grade = "LOW"

        return {
            "total_assets": asset_count,
            "total_active_exposures": total_exposures,
            "density_ratio": round(density_ratio, 3),
            "density_grade": density_grade,
            "top_dense_assets": [
                {"asset_id": str(row[0]), "exposure_count": row[1]}
                for row in per_asset[:10]
            ],
        }

    # =========================================================================
    # SECURITY HEALTH EVALUATION
    # =========================================================================

    async def evaluate_security_health(
        self,
        organization_id: UUID,
    ) -> dict[str, Any]:
        """
        Holistic security health evaluation combining all posture signals.

        Returns the posture score, trend direction, density metrics, and
        actionable health indicators suitable for executive dashboard widgets.
        """
        posture = await self.calculate_posture_score(organization_id)
        trends = await self.analyze_risk_trends(organization_id, days=14)
        density = await self.calculate_exposure_density(organization_id)

        # Health indicators
        indicators = []
        score = posture["score"]

        if score < 50:
            indicators.append({
                "indicator": "LOW_POSTURE_SCORE",
                "severity": "critical",
                "message": f"Security posture score is critically low ({score}/100). Immediate action required.",
            })
        if density["density_ratio"] >= 3:
            indicators.append({
                "indicator": "HIGH_EXPOSURE_DENSITY",
                "severity": "high",
                "message": f"High exposure density ({density['density_ratio']:.1f} exposures/asset). Prioritise remediation.",
            })
        if trends["trend_direction"] == "worsening":
            indicators.append({
                "indicator": "WORSENING_TREND",
                "severity": "high",
                "message": "Risk trend is worsening over the past 14 days.",
            })
        if trends["trend_direction"] == "improving":
            indicators.append({
                "indicator": "IMPROVING_TREND",
                "severity": "info",
                "message": "Risk trend is improving. Remediation efforts are working.",
            })
        if not indicators:
            indicators.append({
                "indicator": "STABLE",
                "severity": "info",
                "message": "Security posture is stable. Continue monitoring.",
            })

        return {
            "posture": posture,
            "trend_summary": {
                "direction": trends["trend_direction"],
                "net_risk_change": trends["net_risk_change"],
                "window_days": 14,
            },
            "density": density,
            "health_indicators": indicators,
            "evaluated_at": datetime.utcnow().isoformat(),
        }

    # =========================================================================
    # INTERNAL SCORING HELPERS
    # =========================================================================

    async def _score_exposure_severity(self, organization_id: UUID) -> float:
        """
        Convert active exposure severity distribution into a 0-100 score.
        Higher score = BETTER posture (fewer/lower severity exposures).
        """
        stmt = select(Exposure.risk_level, func.count(Exposure.id)).where(
            and_(
                Exposure.organization_id == organization_id,
                Exposure.is_active == True,
            )
        ).group_by(Exposure.risk_level)
        result = await self.db.execute(stmt)
        rows = {row[0]: row[1] for row in result.all()}

        if not rows:
            return 100.0  # No exposures = perfect severity score

        total = sum(rows.values())
        weighted_sum = sum(
            rows.get(level, 0) * weight
            for level, weight in _SEV_WEIGHT.items()
        )
        # Normalise: max possible per exposure = 10.0
        normalised_badness = weighted_sum / max(total, 1) / 10.0
        # Invert: good posture = low badness
        return max(0.0, (1.0 - min(normalised_badness, 1.0)) * 100)

    async def _score_exposure_density(self, organization_id: UUID) -> float:
        """
        Score based on exposure-per-asset ratio.  Lower density = better score.
        """
        density = await self.calculate_exposure_density(organization_id)
        ratio = density["density_ratio"]
        # Sigmoid-like mapping: ratio 0→100, ratio 5→0
        return max(0.0, min(100.0, (1 - ratio / 5.0) * 100))

    async def _score_remediation_velocity(self, organization_id: UUID) -> float:
        """
        % of active exposures with a non-null remediation_status → 0-100.
        """
        total_stmt = select(func.count(Exposure.id)).where(
            and_(Exposure.organization_id == organization_id, Exposure.is_active == True)
        )
        remediated_stmt = select(func.count(Exposure.id)).where(
            and_(
                Exposure.organization_id == organization_id,
                Exposure.is_active == True,
                Exposure.remediation_status.isnot(None),
            )
        )
        total = (await self.db.execute(total_stmt)).scalar() or 0
        remediated = (await self.db.execute(remediated_stmt)).scalar() or 0

        if total == 0:
            return 100.0
        return round((remediated / total) * 100, 2)

    async def _score_asset_coverage(self, organization_id: UUID) -> float:
        """
        % of assets seen within last 7 days (recently scanned).
        Approximated by last_seen recency on Asset rows.
        """
        since = datetime.utcnow() - timedelta(days=7)
        total_stmt = select(func.count(Asset.id)).where(
            Asset.organization_id == organization_id
        )
        recent_stmt = select(func.count(Asset.id)).where(
            and_(
                Asset.organization_id == organization_id,
                Asset.last_seen >= since,
            )
        )
        total = (await self.db.execute(total_stmt)).scalar() or 0
        recent = (await self.db.execute(recent_stmt)).scalar() or 0

        if total == 0:
            return 100.0
        return round((recent / total) * 100, 2)

    async def _score_change_momentum(self, organization_id: UUID) -> float:
        """
        Fewer high-severity change events in the last 7 days = better score.
        Max 20 critical/high events → score=0; 0 events → score=100.
        """
        since = datetime.utcnow() - timedelta(days=7)
        stmt = select(func.count(ChangeEvent.id)).where(
            and_(
                ChangeEvent.organization_id == organization_id,
                ChangeEvent.detected_at >= since,
                ChangeEvent.severity.in_(["critical", "high"]),
            )
        )
        count = (await self.db.execute(stmt)).scalar() or 0
        return max(0.0, (1 - count / 20.0) * 100)


def _build_posture_summary(score: float, grade: str, components: dict) -> str:
    """Build a one-line human-readable posture summary."""
    weakest = min(components.items(), key=lambda x: x[1])
    strongest = max(components.items(), key=lambda x: x[1])
    return (
        f"Security posture score: {score}/100 ({grade}). "
        f"Strongest area: {weakest[0].replace('_', ' ')} ({weakest[1]:.0f}). "
        f"Focus area: {strongest[0].replace('_', ' ')} ({strongest[1]:.0f})."
    )
