"""
Reporting Service: generates, persists, and exports executive intelligence reports.

Responsibilities
----------------
- generate_executive_report()    → compose and persist a full ExecutiveReport row
- export_markdown_report()       → retrieve or re-render a report as sanitised Markdown
- build_risk_summary()           → generate a brief risk summary block (reusable)
- generate_attack_surface_report() → detailed attack surface intelligence report

Sanitisation rules
------------------
- All Markdown content is built from structured DB data — never from raw
  user-supplied strings — so injection risk is minimal.
- Organisation names and user-supplied labels are stripped of Markdown
  special characters before embedding.
- No file-system access; export is always returned as a string or DB column.

Architecture
------------
- Modular template functions (_render_*) build individual sections.
- generate_executive_report() orchestrates calls to ExecutiveRiskService
  and PostureService, assembles the payload, and persists the report row.
- Reports are immutable once persisted; re-generation creates a new row.
"""
from __future__ import annotations

import html
import logging
import re
from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import select, and_, desc
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.executive_report import ExecutiveReport, ExecutiveReportType
from backend.models.organization import Organization
from backend.services.executive_risk_service import ExecutiveRiskService
from backend.services.posture_service import PostureService

logger = logging.getLogger(__name__)

# Markdown special characters to strip from user-supplied labels
_MD_ESCAPE_RE = re.compile(r"[`*_{}[\]()#+\-!|>]")


def _sanitise(text: str | None, max_len: int = 500) -> str:
    """Escape Markdown special chars and truncate to max_len."""
    if not text:
        return ""
    cleaned = _MD_ESCAPE_RE.sub("", html.escape(str(text)))
    return cleaned[:max_len]


class ReportingService:
    """
    Executive intelligence reporting engine.

    Generates structured reports, persists them as ExecutiveReport rows,
    and provides sanitised Markdown export for download/email.
    """

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self._exec_svc = ExecutiveRiskService(db)
        self._posture_svc = PostureService(db)

    # =========================================================================
    # GENERATE EXECUTIVE REPORT
    # =========================================================================

    async def generate_executive_report(
        self,
        organization_id: UUID,
        report_type: ExecutiveReportType | str,
        generated_by: UUID | None = None,
        program_id: UUID | None = None,
        custom_title: str | None = None,
    ) -> ExecutiveReport:
        """
        Generate and persist a full executive intelligence report.

        Orchestrates data collection, template rendering, and DB persistence.
        Each call creates a new immutable report row (history is preserved).

        Parameters
        ----------
        organization_id :
            Workspace scope.
        report_type :
            Type of report to generate.
        generated_by :
            UUID of the requesting user (None = system-triggered).
        program_id :
            Optional program scope.
        custom_title :
            Override the auto-generated report title.

        Returns
        -------
        ExecutiveReport
            The persisted, immutable report row.
        """
        rt = ExecutiveReportType(report_type) if isinstance(report_type, str) else report_type

        # Fetch org name for report header
        org_stmt = select(Organization).where(Organization.id == organization_id)
        org_result = await self.db.execute(org_stmt)
        org = org_result.scalars().first()
        org_name = _sanitise(org.name if org else "Unknown Organisation")

        # Collect intelligence data
        report_data, summary, markdown = await self._collect_report_data(
            organization_id=organization_id,
            report_type=rt,
            org_name=org_name,
            program_id=program_id,
        )

        # Build title
        timestamp = datetime.utcnow().strftime("%Y-%m-%d")
        type_labels = {
            ExecutiveReportType.EXPOSURE_SUMMARY: "Exposure Summary Report",
            ExecutiveReportType.ATTACK_SURFACE_REPORT: "Attack Surface Intelligence Report",
            ExecutiveReportType.EXECUTIVE_BRIEF: "Executive Security Brief",
            ExecutiveReportType.RISK_TRENDS: "Risk Trends Analysis",
            ExecutiveReportType.POSTURE_REPORT: "Security Posture Scorecard",
        }
        auto_title = f"{org_name} — {type_labels.get(rt, 'Executive Report')} — {timestamp}"
        title = _sanitise(custom_title, max_len=512) if custom_title else auto_title

        # Persist immutable report row
        report = ExecutiveReport(
            organization_id=organization_id,
            program_id=program_id,
            report_type=rt,
            title=title,
            summary=summary,
            report_data=report_data,
            content_markdown=markdown,
            generated_by=generated_by,
        )
        self.db.add(report)
        await self.db.commit()
        await self.db.refresh(report)

        logger.info(
            "ExecutiveReport generated: id=%s type=%s org=%s",
            report.id, rt.value, organization_id,
        )
        return report

    # =========================================================================
    # MARKDOWN EXPORT
    # =========================================================================

    async def export_markdown_report(
        self,
        organization_id: UUID,
        report_id: UUID,
    ) -> str | None:
        """
        Retrieve a persisted report's sanitised Markdown content.

        Returns None if the report doesn't exist or doesn't belong to
        the given organisation (workspace isolation enforced).
        """
        stmt = select(ExecutiveReport).where(
            and_(
                ExecutiveReport.id == report_id,
                ExecutiveReport.organization_id == organization_id,
            )
        )
        result = await self.db.execute(stmt)
        report = result.scalars().first()

        if report is None:
            return None
        return report.content_markdown or ""

    # =========================================================================
    # RISK SUMMARY (REUSABLE BLOCK)
    # =========================================================================

    async def build_risk_summary(
        self,
        organization_id: UUID,
    ) -> dict[str, Any]:
        """
        Build a concise risk summary block.  Reusable by dashboard endpoints
        without persisting a full report row.
        """
        posture = await self._posture_svc.calculate_posture_score(organization_id)
        exposure_risk = await self._exec_svc.summarize_exposure_risk(organization_id, top_n=5)
        growth = await self._exec_svc.analyze_attack_surface_growth(organization_id, days=7)

        return {
            "posture_score": posture["score"],
            "posture_grade": posture["grade"],
            "posture_emoji": posture["grade_emoji"],
            "total_active_exposures": exposure_risk["total_active"],
            "critical_exposures": exposure_risk["severity_breakdown"].get("critical", 0),
            "high_exposures": exposure_risk["severity_breakdown"].get("high", 0),
            "critical_backlog": exposure_risk["critical_backlog"],
            "surface_momentum": growth["surface_momentum"],
            "net_asset_growth_7d": growth["net_asset_growth"],
            "top_exposures": exposure_risk["top_exposures"][:5],
            "summary_generated_at": datetime.utcnow().isoformat(),
        }

    # =========================================================================
    # ATTACK SURFACE REPORT
    # =========================================================================

    async def generate_attack_surface_report(
        self,
        organization_id: UUID,
        program_id: UUID | None = None,
    ) -> dict[str, Any]:
        """
        Generate a detailed attack surface intelligence report payload.

        Returns a plain dict (not persisted) suitable for inline display
        or as the ``report_data`` payload of an ATTACK_SURFACE_REPORT row.
        """
        posture = await self._exec_svc.calculate_security_posture(organization_id)
        exposure_risk = await self._exec_svc.summarize_exposure_risk(organization_id, top_n=20)
        growth = await self._exec_svc.analyze_attack_surface_growth(organization_id, days=30)
        insights = await self._exec_svc.generate_executive_insights(organization_id)
        density = await self._posture_svc.calculate_exposure_density(organization_id)

        return {
            "security_posture": posture,
            "exposure_risk_summary": exposure_risk,
            "attack_surface_growth": growth,
            "executive_insights": insights,
            "exposure_density": density,
            "report_generated_at": datetime.utcnow().isoformat(),
        }

    # =========================================================================
    # REPORT HISTORY RETRIEVAL
    # =========================================================================

    async def list_reports(
        self,
        organization_id: UUID,
        report_type: ExecutiveReportType | str | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> dict[str, Any]:
        """
        List historical executive reports (metadata only, no content payload).

        Workspace isolation enforced — only reports for ``organization_id``.
        """
        conditions = [ExecutiveReport.organization_id == organization_id]
        if report_type is not None:
            rt = ExecutiveReportType(report_type) if isinstance(report_type, str) else report_type
            conditions.append(ExecutiveReport.report_type == rt)

        from sqlalchemy import func
        total_stmt = select(func.count(ExecutiveReport.id)).where(and_(*conditions))
        total = (await self.db.execute(total_stmt)).scalar() or 0

        stmt = (
            select(ExecutiveReport)
            .where(and_(*conditions))
            .order_by(desc(ExecutiveReport.created_at))
            .limit(limit)
            .offset(offset)
        )
        result = await self.db.execute(stmt)
        reports = result.scalars().all()

        return {
            "reports": [
                {
                    "id": str(r.id),
                    "report_type": r.report_type,
                    "title": r.title,
                    "summary": r.summary,
                    "generated_by": str(r.generated_by) if r.generated_by else None,
                    "created_at": r.created_at.isoformat() if r.created_at else None,
                }
                for r in reports
            ],
            "total": total,
            "limit": limit,
            "offset": offset,
        }

    # =========================================================================
    # INTERNAL DATA COLLECTION + TEMPLATE ENGINE
    # =========================================================================

    async def _collect_report_data(
        self,
        organization_id: UUID,
        report_type: ExecutiveReportType,
        org_name: str,
        program_id: UUID | None,
    ) -> tuple[dict, str, str]:
        """
        Collect raw intelligence data and render payload + Markdown for a report type.

        Returns
        -------
        (report_data, summary, content_markdown)
        """
        if report_type == ExecutiveReportType.POSTURE_REPORT:
            data = await self._exec_svc.calculate_security_posture(organization_id)
            summary = (
                f"Security posture score: {data['score']}/100 ({data['grade']}). "
                f"{data.get('posture_summary', '')}"
            )
            md = _render_posture_report(org_name, data)

        elif report_type == ExecutiveReportType.EXPOSURE_SUMMARY:
            data = await self._exec_svc.summarize_exposure_risk(organization_id, top_n=20)
            sev = data["severity_breakdown"]
            summary = (
                f"{data['total_active']} active exposures across {data['affected_assets']} assets. "
                f"Critical: {sev.get('critical', 0)}, High: {sev.get('high', 0)}. "
                f"Unaddressed backlog: {data['critical_backlog']} critical/high items."
            )
            md = _render_exposure_summary(org_name, data)

        elif report_type == ExecutiveReportType.ATTACK_SURFACE_REPORT:
            data = await self.generate_attack_surface_report(organization_id, program_id)
            posture = data["security_posture"]
            summary = (
                f"Attack surface analysis: posture {posture['score']}/100 ({posture['grade']}). "
                f"Surface momentum: {data['attack_surface_growth']['surface_momentum']}. "
                f"Exposure density: {data['exposure_density']['density_ratio']:.2f}x."
            )
            md = _render_attack_surface_report(org_name, data)

        elif report_type == ExecutiveReportType.RISK_TRENDS:
            data = await self._posture_svc.analyze_risk_trends(organization_id, days=30)
            summary = (
                f"30-day risk trend: {data['trend_direction']}. "
                f"Net risk change: {data['net_risk_change']:+.1f}. "
                f"{data['total_events']} change events detected."
            )
            md = _render_risk_trends_report(org_name, data)

        else:  # EXECUTIVE_BRIEF
            posture_data = await self._exec_svc.calculate_security_posture(organization_id)
            insights_data = await self._exec_svc.generate_executive_insights(organization_id)
            exposure_data = await self._exec_svc.summarize_exposure_risk(organization_id, top_n=10)
            data = {
                "posture": posture_data,
                "insights": insights_data,
                "exposure_summary": exposure_data,
            }
            summary = (
                f"Executive brief: posture {posture_data['score']}/100 ({posture_data['grade']}). "
                f"{len(insights_data['critical_insights'])} critical insights. "
                f"{exposure_data['total_active']} active exposures."
            )
            md = _render_executive_brief(org_name, data)

        return data, _sanitise(summary, max_len=1000), md


# =============================================================================
# MARKDOWN TEMPLATE RENDERERS (module-level helpers)
# =============================================================================

def _header(org_name: str, report_title: str) -> str:
    ts = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    return (
        f"# {report_title}\n\n"
        f"**Organisation**: {org_name}  \n"
        f"**Generated**: {ts}  \n"
        f"**Platform**: NisargHunter AI — EASM Intelligence Platform\n\n---\n\n"
    )


def _render_posture_report(org_name: str, data: dict) -> str:
    md = _header(org_name, "Security Posture Scorecard")
    score = data.get("score", 0)
    grade = data.get("grade", "N/A")
    emoji = data.get("grade_emoji", "")
    md += f"## {emoji} Posture Score: {score}/100 — {grade}\n\n"
    md += f"> {data.get('posture_summary', '')}\n\n"

    md += "## Component Breakdown\n\n"
    md += "| Component | Score |\n|---|---|\n"
    for comp, val in (data.get("components") or {}).items():
        md += f"| {comp.replace('_', ' ').title()} | {val:.1f}/100 |\n"

    md += "\n## Attack Surface KPIs\n\n"
    kpis = data.get("kpis") or {}
    md += f"- **Total Assets**: {kpis.get('total_assets', 0)}\n"
    md += f"- **Alive Assets**: {kpis.get('alive_assets', 0)}\n"
    md += f"- **Active Exposures**: {kpis.get('active_exposures', 0)}\n"
    md += f"- **Critical Exposures**: {kpis.get('critical_exposures', 0)}\n"
    md += f"- **Exposures/Asset Ratio**: {kpis.get('exposure_per_asset', 0):.2f}\n"
    md += f"- **Open Findings**: {kpis.get('open_findings', 0)}\n"

    md += "\n## Top Action Items\n\n"
    for item in (data.get("action_items") or [])[:5]:
        md += f"{item['rank']}. **{_sanitise(item['title'])}** — Risk Score: {item['risk_score']} — {_sanitise(item['action'])}\n"

    return md


def _render_exposure_summary(org_name: str, data: dict) -> str:
    md = _header(org_name, "Exposure Summary Report")
    sev = data.get("severity_breakdown", {})
    md += f"## Overview\n\n"
    md += f"- **Total Active Exposures**: {data.get('total_active', 0)}\n"
    md += f"- **Affected Assets**: {data.get('affected_assets', 0)}\n"
    md += f"- **Mean Risk Score**: {data.get('mean_risk_score', 0):.1f}/100\n"
    md += f"- **Critical Backlog**: {data.get('critical_backlog', 0)} unaddressed critical/high\n\n"

    md += "## Severity Breakdown\n\n"
    md += "| Severity | Count |\n|---|---|\n"
    for level in ["critical", "high", "medium", "low", "info"]:
        md += f"| {level.upper()} | {sev.get(level, 0)} |\n"

    md += "\n## Top Prioritised Exposures\n\n"
    md += "| Rank | Title | Type | Risk Level | Risk Score | Days Open |\n|---|---|---|---|---|---|\n"
    for i, exp in enumerate((data.get("top_exposures") or [])[:10], 1):
        md += (
            f"| {i} | {_sanitise(exp.get('title'), 60)} | "
            f"{exp.get('exposure_type', '')} | {exp.get('risk_level', '').upper()} | "
            f"{exp.get('risk_score', 0):.1f} | {exp.get('days_open', 'N/A')} |\n"
        )

    md += "\n## Exposure Type Distribution\n\n"
    md += "| Type | Count |\n|---|---|\n"
    for etype, count in list((data.get("exposure_types") or {}).items())[:10]:
        md += f"| {etype.replace('_', ' ').title()} | {count} |\n"

    return md


def _render_attack_surface_report(org_name: str, data: dict) -> str:
    md = _header(org_name, "Attack Surface Intelligence Report")

    posture = data.get("security_posture", {})
    md += f"## Security Posture\n\n"
    md += f"**Score**: {posture.get('score', 0)}/100 — **{posture.get('grade', 'N/A')}** {posture.get('grade_emoji', '')}\n\n"

    growth = data.get("attack_surface_growth", {})
    counts = growth.get("current_counts", {})
    md += "## Attack Surface Inventory\n\n"
    md += f"| Metric | Value |\n|---|---|\n"
    md += f"| Total Assets | {counts.get('assets', 0)} |\n"
    md += f"| Total Endpoints | {counts.get('endpoints', 0)} |\n"
    md += f"| Active Exposures | {counts.get('active_exposures', 0)} |\n"
    md += f"| Surface Momentum | {growth.get('surface_momentum', 'N/A').upper()} |\n"
    md += f"| Net Asset Growth (30d) | {growth.get('net_asset_growth', 0):+d} |\n\n"

    density = data.get("exposure_density", {})
    md += "## Exposure Density\n\n"
    md += f"- **Density Ratio**: {density.get('density_ratio', 0):.2f} exposures/asset\n"
    md += f"- **Density Grade**: {density.get('density_grade', 'N/A')}\n\n"

    insights = data.get("executive_insights", {})
    md += "## Executive Insights\n\n"
    for insight in (insights.get("critical_insights") or [])[:3]:
        md += f"🚨 **CRITICAL**: {_sanitise(insight.get('insight'))}\n\n"
    for insight in (insights.get("risk_insights") or [])[:3]:
        md += f"⚠️ **RISK**: {_sanitise(insight.get('insight'))}\n\n"
    for rec in (insights.get("strategic_recommendations") or [])[:3]:
        md += f"### {rec.get('priority', '')}. {_sanitise(rec.get('title'))}\n{_sanitise(rec.get('recommendation'))}\n\n"

    return md


def _render_risk_trends_report(org_name: str, data: dict) -> str:
    md = _header(org_name, "Risk Trends Analysis (30-Day)")
    md += f"## Trend Summary\n\n"
    md += f"- **Direction**: {data.get('trend_direction', 'N/A').upper()}\n"
    md += f"- **Total Events**: {data.get('total_events', 0)}\n"
    md += f"- **Net Risk Change**: {data.get('net_risk_change', 0):+.2f}\n\n"

    md += "## Daily Risk Timeline\n\n"
    md += "| Date | Events | Daily Delta | Cumulative Risk |\n|---|---|---|---|\n"
    for point in (data.get("trend_series") or [])[-14:]:
        md += (
            f"| {point.get('date', 'N/A')} | {point.get('total_events', 0)} | "
            f"{point.get('daily_delta', 0):+.1f} | {point.get('cumulative_risk', 0):.1f} |\n"
        )
    return md


def _render_executive_brief(org_name: str, data: dict) -> str:
    md = _header(org_name, "Executive Security Brief")

    posture = data.get("posture", {})
    md += f"## {posture.get('grade_emoji', '')} Security Posture: {posture.get('score', 0)}/100 ({posture.get('grade', 'N/A')})\n\n"
    md += f"> {posture.get('posture_summary', '')}\n\n"

    exposure = data.get("exposure_summary", {})
    sev = exposure.get("severity_breakdown", {})
    md += "## Exposure Snapshot\n\n"
    md += f"- **Total Active**: {exposure.get('total_active', 0)} exposures on {exposure.get('affected_assets', 0)} assets\n"
    md += f"- **Critical/High Backlog**: {exposure.get('critical_backlog', 0)} unaddressed\n"
    md += f"- 🚨 Critical: {sev.get('critical', 0)} | ⚠️ High: {sev.get('high', 0)} | Medium: {sev.get('medium', 0)}\n\n"

    insights = data.get("insights", {})
    md += "## Critical Intelligence\n\n"
    for item in (insights.get("critical_insights") or [])[:3]:
        md += f"- 🚨 {_sanitise(item.get('insight'))}\n"
    for item in (insights.get("risk_insights") or [])[:3]:
        md += f"- ⚠️ {_sanitise(item.get('insight'))}\n"
    md += "\n"

    md += "## Strategic Recommendations\n\n"
    for rec in (insights.get("strategic_recommendations") or [])[:3]:
        md += f"**{rec.get('priority', '')}. {_sanitise(rec.get('title'))}**\n{_sanitise(rec.get('recommendation'))}\n\n"

    return md
