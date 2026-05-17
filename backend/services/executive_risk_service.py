"""
Executive Risk Service: aggregates intelligence into executive-level insights.

This service is the primary intelligence aggregation layer for the executive
dashboard and reporting engine.  It pulls together data from multiple domain
services (RiskService, PostureService, timeline data) into a coherent
executive intelligence picture.

Responsibilities
----------------
- calculate_security_posture()   → delegates to PostureService, enriches result
- summarize_exposure_risk()      → top exposures, severity breakdown, KPIs
- analyze_attack_surface_growth() → asset/endpoint count trends
- generate_executive_insights()  → narrative intelligence bullets for C-suite

Security rules
--------------
- All queries scoped to organization_id.
- No cross-tenant data access.
- All returned data is plain dict (no ORM objects).
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import select, and_, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.asset import Asset
from backend.models.endpoint import Endpoint
from backend.models.exposure import Exposure
from backend.models.finding import Finding
from backend.models.change_event import ChangeEvent
from backend.services.posture_service import PostureService
from backend.services.risk_service import RiskService

logger = logging.getLogger(__name__)

# Severity ordering for sorting
_SEV_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}


class ExecutiveRiskService:
    """
    Aggregates executive-level security intelligence for dashboards and reports.
    """

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self._posture = PostureService(db)
        self._risk = RiskService(db)

    # =========================================================================
    # SECURITY POSTURE
    # =========================================================================

    async def calculate_security_posture(
        self,
        organization_id: UUID,
    ) -> dict[str, Any]:
        """
        Calculate and enrich the security posture for executive consumption.

        Delegates the score calculation to PostureService and enriches with
        KPI comparison data (vs. previous period) and prioritised action items.

        Returns
        -------
        dict with:
            posture_score     – 0-100 composite score
            grade             – EXCELLENT / GOOD / MEDIUM / HIGH_RISK / CRITICAL
            components        – per-component breakdown
            kpis              – attack surface KPIs (counts, ratios)
            action_items      – top 5 prioritised remediation actions
            posture_summary   – one-line narrative
        """
        # Core posture score
        posture = await self._posture.calculate_posture_score(organization_id)

        # Enrich with KPIs
        kpis = await self._build_surface_kpis(organization_id)

        # Top action items (highest-risk unresolved exposures)
        action_items = await self._build_action_items(organization_id)

        return {
            **posture,
            "kpis": kpis,
            "action_items": action_items,
        }

    # =========================================================================
    # EXPOSURE RISK SUMMARY
    # =========================================================================

    async def summarize_exposure_risk(
        self,
        organization_id: UUID,
        top_n: int = 10,
    ) -> dict[str, Any]:
        """
        Summarise the current exposure risk landscape.

        Returns
        -------
        dict with:
            total_active        – count of active exposures
            severity_breakdown  – counts by risk level
            top_exposures       – top N ranked by risk_score (desc)
            exposure_types      – distribution by exposure_type
            affected_assets     – count of assets with ≥1 active exposure
            mean_risk_score     – average risk_score across active exposures
            critical_backlog    – count of critical/high with no remediation
        """
        stmt = select(Exposure).where(
            and_(
                Exposure.organization_id == organization_id,
                Exposure.is_active == True,
            )
        ).order_by(desc(Exposure.risk_score))
        result = await self.db.execute(stmt)
        exposures = result.scalars().all()

        if not exposures:
            return {
                "total_active": 0,
                "severity_breakdown": {s: 0 for s in ["critical", "high", "medium", "low", "info"]},
                "top_exposures": [],
                "exposure_types": {},
                "affected_assets": 0,
                "mean_risk_score": 0.0,
                "critical_backlog": 0,
            }

        sev_breakdown: dict[str, int] = {s: 0 for s in ["critical", "high", "medium", "low", "info"]}
        type_dist: dict[str, int] = {}
        affected_assets: set = set()
        critical_backlog = 0
        total_score = 0.0

        for e in exposures:
            lvl = e.risk_level if isinstance(e.risk_level, str) else e.risk_level.value
            if lvl in sev_breakdown:
                sev_breakdown[lvl] += 1
            et = e.exposure_type if isinstance(e.exposure_type, str) else e.exposure_type.value
            type_dist[et] = type_dist.get(et, 0) + 1
            affected_assets.add(e.asset_id)
            total_score += e.risk_score
            if lvl in ("critical", "high") and not e.remediation_status:
                critical_backlog += 1

        top_exposures = [
            {
                "id": str(e.id),
                "title": e.title,
                "exposure_type": e.exposure_type if isinstance(e.exposure_type, str) else e.exposure_type.value,
                "risk_level": e.risk_level if isinstance(e.risk_level, str) else e.risk_level.value,
                "risk_score": round(e.risk_score, 2),
                "asset_id": str(e.asset_id),
                "first_detected": e.first_detected.isoformat() if e.first_detected else None,
                "days_open": (datetime.utcnow() - e.first_detected).days if e.first_detected else None,
                "remediation_status": e.remediation_status,
            }
            for e in exposures[:top_n]
        ]

        return {
            "total_active": len(exposures),
            "severity_breakdown": sev_breakdown,
            "top_exposures": top_exposures,
            "exposure_types": dict(sorted(type_dist.items(), key=lambda x: x[1], reverse=True)),
            "affected_assets": len(affected_assets),
            "mean_risk_score": round(total_score / len(exposures), 2),
            "critical_backlog": critical_backlog,
        }

    # =========================================================================
    # ATTACK SURFACE GROWTH
    # =========================================================================

    async def analyze_attack_surface_growth(
        self,
        organization_id: UUID,
        days: int = 30,
    ) -> dict[str, Any]:
        """
        Analyse attack surface growth over the specified window.

        Returns asset/endpoint/exposure count trends with week-over-week
        comparison and net growth rate.

        Returns
        -------
        dict with:
            current_counts    – assets, endpoints, exposures (current)
            growth_events     – new/removed asset events over the window
            weekly_growth     – [{"week", "new_assets", "removed_assets"}]
            net_asset_growth  – total new minus removed
            surface_momentum  – "expanding" | "contracting" | "stable"
        """
        since = datetime.utcnow() - timedelta(days=days)

        # Current inventory counts
        asset_count = (await self.db.execute(
            select(func.count(Asset.id)).where(Asset.organization_id == organization_id)
        )).scalar() or 0

        endpoint_count = (await self.db.execute(
            select(func.count(Endpoint.id)).join(
                Asset, Endpoint.asset_id == Asset.id
            ).where(Asset.organization_id == organization_id)
        )).scalar() or 0

        exposure_count = (await self.db.execute(
            select(func.count(Exposure.id)).where(
                and_(
                    Exposure.organization_id == organization_id,
                    Exposure.is_active == True,
                )
            )
        )).scalar() or 0

        # Change events for asset growth
        growth_stmt = select(ChangeEvent).where(
            and_(
                ChangeEvent.organization_id == organization_id,
                ChangeEvent.change_type.in_(["new_asset", "removed_asset"]),
                ChangeEvent.detected_at >= since,
            )
        ).order_by(ChangeEvent.detected_at)
        growth_events = (await self.db.execute(growth_stmt)).scalars().all()

        # Weekly aggregation
        weekly: dict[str, dict[str, int]] = {}
        for e in growth_events:
            wk = e.detected_at.strftime("%Y-W%W") if e.detected_at else "unknown"
            weekly.setdefault(wk, {"week": wk, "new_assets": 0, "removed_assets": 0})
            if e.change_type == "new_asset":
                weekly[wk]["new_assets"] += 1
            else:
                weekly[wk]["removed_assets"] += 1

        new_total = sum(1 for e in growth_events if e.change_type == "new_asset")
        removed_total = sum(1 for e in growth_events if e.change_type == "removed_asset")
        net_growth = new_total - removed_total

        momentum = "expanding" if net_growth > 0 else ("contracting" if net_growth < 0 else "stable")

        return {
            "current_counts": {
                "assets": asset_count,
                "endpoints": endpoint_count,
                "active_exposures": exposure_count,
            },
            "growth_events": {
                "new_assets": new_total,
                "removed_assets": removed_total,
                "window_days": days,
            },
            "weekly_growth": sorted(weekly.values(), key=lambda x: x["week"]),
            "net_asset_growth": net_growth,
            "surface_momentum": momentum,
        }

    # =========================================================================
    # EXECUTIVE INSIGHTS
    # =========================================================================

    async def generate_executive_insights(
        self,
        organization_id: UUID,
    ) -> dict[str, Any]:
        """
        Generate narrative intelligence bullets for C-suite consumption.

        Combines posture score, exposure risk, surface growth, and trend data
        into a structured set of insight bullets with priority levels.

        Returns
        -------
        dict with:
            critical_insights   – list of critical-priority intelligence bullets
            risk_insights       – list of risk-level bullets
            positive_insights   – list of positive/improving signals
            strategic_recommendations – top 3 strategic recommendations
            generated_at        – ISO timestamp
        """
        # Gather intelligence
        posture = await self._posture.calculate_posture_score(organization_id)
        exposure_summary = await self.summarize_exposure_risk(organization_id)
        growth = await self.analyze_attack_surface_growth(organization_id, days=14)
        health = await self._posture.evaluate_security_health(organization_id)

        critical_insights: list[dict] = []
        risk_insights: list[dict] = []
        positive_insights: list[dict] = []

        score = posture["score"]
        sev = exposure_summary["severity_breakdown"]

        # Critical insights
        if sev.get("critical", 0) > 0:
            critical_insights.append({
                "priority": "CRITICAL",
                "insight": f"{sev['critical']} critical severity exposure(s) require immediate remediation.",
                "metric": sev["critical"],
                "action": "Review and remediate critical exposures immediately.",
            })
        if exposure_summary["critical_backlog"] > 5:
            critical_insights.append({
                "priority": "CRITICAL",
                "insight": f"Remediation backlog: {exposure_summary['critical_backlog']} critical/high exposures have no remediation plan.",
                "metric": exposure_summary["critical_backlog"],
                "action": "Assign owners and start remediation for all backlogged exposures.",
            })
        if score < 40:
            critical_insights.append({
                "priority": "CRITICAL",
                "insight": f"Security posture score ({score}/100) indicates critical organisational risk.",
                "metric": score,
                "action": "Initiate an emergency security posture review.",
            })

        # Risk insights
        if sev.get("high", 0) > 0:
            risk_insights.append({
                "priority": "HIGH",
                "insight": f"{sev['high']} high-severity exposure(s) detected across the attack surface.",
                "metric": sev["high"],
                "action": "Schedule remediation within 72 hours.",
            })
        if growth["surface_momentum"] == "expanding":
            risk_insights.append({
                "priority": "HIGH",
                "insight": f"Attack surface is expanding: +{growth['growth_events']['new_assets']} new assets in last 14 days.",
                "metric": growth["growth_events"]["new_assets"],
                "action": "Review all new assets for exposure coverage.",
            })
        density = health["density"]["density_ratio"]
        if density > 2:
            risk_insights.append({
                "priority": "MEDIUM",
                "insight": f"Exposure density is elevated at {density:.1f} exposures per asset.",
                "metric": density,
                "action": "Focus remediation on high-density asset clusters.",
            })

        # Positive insights
        if health["trend_summary"]["direction"] == "improving":
            positive_insights.append({
                "priority": "INFO",
                "insight": "Risk trend is improving over the past 14 days. Remediation efforts are effective.",
                "action": "Continue current remediation velocity.",
            })
        if posture["components"].get("remediation_velocity", 0) > 70:
            positive_insights.append({
                "priority": "INFO",
                "insight": f"Strong remediation velocity ({posture['components']['remediation_velocity']:.0f}/100). Team is actively resolving exposures.",
                "action": "Maintain current remediation pace.",
            })

        # Strategic recommendations
        recommendations = _build_strategic_recommendations(posture, exposure_summary, growth)

        return {
            "critical_insights": critical_insights,
            "risk_insights": risk_insights,
            "positive_insights": positive_insights,
            "strategic_recommendations": recommendations,
            "posture_score": score,
            "posture_grade": posture["grade"],
            "generated_at": datetime.utcnow().isoformat(),
        }

    # =========================================================================
    # HELPERS
    # =========================================================================

    async def _build_surface_kpis(self, organization_id: UUID) -> dict[str, Any]:
        """Build attack surface KPI snapshot."""
        asset_count = (await self.db.execute(
            select(func.count(Asset.id)).where(Asset.organization_id == organization_id)
        )).scalar() or 0

        alive_count = (await self.db.execute(
            select(func.count(Asset.id)).where(
                and_(Asset.organization_id == organization_id, Asset.is_alive == True)
            )
        )).scalar() or 0

        active_exposures = (await self.db.execute(
            select(func.count(Exposure.id)).where(
                and_(Exposure.organization_id == organization_id, Exposure.is_active == True)
            )
        )).scalar() or 0

        critical_exposures = (await self.db.execute(
            select(func.count(Exposure.id)).where(
                and_(
                    Exposure.organization_id == organization_id,
                    Exposure.is_active == True,
                    Exposure.risk_level == "critical",
                )
            )
        )).scalar() or 0

        open_findings = (await self.db.execute(
            select(func.count(Finding.id)).where(
                and_(
                    Finding.organization_id == organization_id,
                    Finding.status == "open",
                )
            )
        )).scalar() or 0

        return {
            "total_assets": asset_count,
            "alive_assets": alive_count,
            "asset_alive_ratio": round(alive_count / max(asset_count, 1), 3),
            "active_exposures": active_exposures,
            "critical_exposures": critical_exposures,
            "exposure_per_asset": round(active_exposures / max(asset_count, 1), 2),
            "open_findings": open_findings,
        }

    async def _build_action_items(self, organization_id: UUID) -> list[dict[str, Any]]:
        """Build top 5 prioritised action items from unresolved exposures."""
        priorities = await self._risk.get_remediation_priorities(
            organization_id=organization_id,
            limit=5,
        )
        return [
            {
                "rank": i + 1,
                "title": p["title"],
                "exposure_id": p["exposure_id"],
                "asset_id": p["asset_id"],
                "risk_score": p["risk_score"],
                "exposure_type": p["type"],
                "days_exposed": p["days_exposed"],
                "action": f"Remediate {p['type'].replace('_', ' ')} on asset {p['asset_id'][:8]}…",
            }
            for i, p in enumerate(priorities)
        ]


def _build_strategic_recommendations(
    posture: dict,
    exposure_summary: dict,
    growth: dict,
) -> list[dict[str, str]]:
    """Build 3 strategic recommendations based on current intelligence."""
    recs = []

    # Remediation-based recommendation
    backlog = exposure_summary.get("critical_backlog", 0)
    if backlog > 0:
        recs.append({
            "priority": "1",
            "title": "Accelerate Critical Exposure Remediation",
            "recommendation": (
                f"Assign dedicated resources to resolve {backlog} critical/high "
                "exposures with no remediation plan. Target < 72-hour resolution for critical items."
            ),
        })

    # Attack surface hygiene
    if growth["surface_momentum"] == "expanding":
        recs.append({
            "priority": "2",
            "title": "Tighten Asset Exposure Coverage",
            "recommendation": (
                "Attack surface is expanding. Implement mandatory exposure scanning "
                "for all newly discovered assets within 24 hours of detection."
            ),
        })

    # Posture improvement
    weak_component = min(
        posture["components"].items(), key=lambda x: x[1], default=("unknown", 0)
    )
    recs.append({
        "priority": str(len(recs) + 1),
        "title": f"Improve {weak_component[0].replace('_', ' ').title()}",
        "recommendation": (
            f"The weakest posture component is '{weak_component[0].replace('_', ' ')}' "
            f"(score: {weak_component[1]:.0f}/100). Focus improvement efforts here for maximum posture gain."
        ),
    })

    return recs[:3]
