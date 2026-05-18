"""
Report service orchestrating AI-assisted draft creation and quality evaluation.
"""
from __future__ import annotations

import re
from typing import Any
from uuid import UUID

from sqlalchemy import and_, desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.ai.report_writer import generate_report
from backend.models.finding import Finding
from backend.models.report_draft import ReportDraft
from backend.models.triage_result import TriageResult
from backend.services.quality_score_service import QualityScoreService
from backend.services.remediation_service import RemediationService


class ReportService:
    """Coordinates context enrichment, report generation, scoring, and draft persistence."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.quality_service = QualityScoreService()
        self.remediation_service = RemediationService()

    def _extract_high_signal_tags(self, context: dict[str, Any]) -> list[str]:
        text = " ".join(
            [
                str(context.get("title") or ""),
                str(context.get("description") or ""),
                str(context.get("endpoint") or ""),
            ]
        ).lower()

        tags: list[str] = []
        patterns = {
            "auth_bypass": r"auth|login|oauth|sso|bypass",
            "admin_exposure": r"admin|internal|dashboard",
            "api_vulnerability": r"\bapi\b|idor|bola|mass assignment",
            "ssrf_risk": r"ssrf|server[-\s]?side request",
            "cloud_exposure": r"s3|bucket|iam|cloud|metadata",
            "graphql_weakness": r"graphql|introspection",
            "upload_surface": r"upload|file|multipart",
            "sensitive_data_exposure": r"pii|secret|token|credential|sensitive",
        }
        for name, pattern in patterns.items():
            if re.search(pattern, text):
                tags.append(name)
        return tags

    async def enrich_report_context(self, finding_id: UUID, organization_id: UUID) -> dict[str, Any]:
        """Assemble finding + latest triage context for factual report drafting."""
        finding_result = await self.db.execute(
            select(Finding).where(
                and_(
                    Finding.id == finding_id,
                    Finding.organization_id == organization_id,
                )
            )
        )
        finding = finding_result.scalars().first()
        if not finding:
            raise ValueError("Finding not found in organization scope")

        triage_result = await self.db.execute(
            select(TriageResult)
            .where(
                and_(
                    TriageResult.finding_id == finding_id,
                    TriageResult.organization_id == organization_id,
                )
            )
            .order_by(desc(TriageResult.created_at))
            .limit(1)
        )
        latest_triage = triage_result.scalars().first()

        scanner_severity = str(getattr(finding.severity, "value", finding.severity)).lower()
        endpoint = str(finding.endpoint or "")

        context = {
            "finding_id": str(finding.id),
            "organization_id": str(organization_id),
            "title": finding.title,
            "severity": scanner_severity,
            "description": finding.description,
            "summary": finding.description,
            "technical_details": finding.description,
            "affected_asset": endpoint,
            "endpoint": endpoint,
            "evidence": finding.evidence or "",
            "triage_summary": latest_triage.ai_summary if latest_triage else "",
            "triage_reasoning": latest_triage.reasoning if latest_triage else "",
            "confidence_score": float(latest_triage.confidence_score) if latest_triage else 0.0,
            "exploitability_score": float(latest_triage.exploitability_score) if latest_triage else 0.0,
        }

        context["high_signal_tags"] = self._extract_high_signal_tags(context)
        context["vulnerability_type"] = finding.title
        context["technology_stack"] = "web application"
        context["asset_type"] = "api" if "api" in endpoint.lower() else "web"
        context["references"] = [
            "OWASP Testing Guide",
            "CWE catalog",
        ]

        return context

    def format_platform_report(self, report_data: dict[str, Any], platform: str) -> str:
        """Render deterministic report markdown with required section ordering."""
        heading = f"Platform: {platform.title()}"

        def _list_block(items: list[str]) -> str:
            safe = [str(item).strip() for item in items if str(item).strip()]
            if not safe:
                return "- N/A"
            return "\n".join(f"- {item}" for item in safe)

        references = _list_block(report_data.get("references", []))
        repro_steps = _list_block(report_data.get("steps_to_reproduce", []))
        remediation_steps = _list_block(report_data.get("remediation_steps", []))

        return (
            f"# {report_data.get('title', 'Untitled Vulnerability')}\n\n"
            f"{heading}\n\n"
            f"## Severity\n{report_data.get('severity', 'Medium')}\n\n"
            f"## Summary\n{report_data.get('summary', '')}\n\n"
            f"## Affected Asset\n{report_data.get('affected_asset', '')}\n\n"
            f"## Steps to Reproduce\n{repro_steps}\n\n"
            f"## Technical Details\n{report_data.get('technical_details', '')}\n\n"
            f"## Business Impact\n{report_data.get('business_impact', '')}\n\n"
            f"## Evidence\n{report_data.get('evidence', '')}\n\n"
            f"## Remediation\n{report_data.get('remediation', '')}\n\n"
            f"### Remediation Steps\n{remediation_steps}\n\n"
            f"## References\n{references}\n\n"
            "## Human Review Requirement\n"
            "This draft is advisory-only and requires human validation before submission.\n"
        )

    async def create_report_draft(
        self,
        finding_id: UUID,
        organization_id: UUID,
        platform: str = "hackerone",
    ) -> dict[str, Any]:
        """Generate, score, and persist a report draft for human review."""
        context = await self.enrich_report_context(finding_id, organization_id)
        report_data = await generate_report(context, platform=platform, organization_id=str(organization_id))

        remediation_data = await self.remediation_service.generate_remediation_guidance(
            context,
            organization_id=str(organization_id),
        )
        if remediation_data.get("remediation_summary"):
            report_data["remediation"] = remediation_data["remediation_summary"]
        if remediation_data.get("fix_steps"):
            report_data["remediation_steps"] = remediation_data["fix_steps"]

        quality = self.quality_service.calculate_quality_score(report_data)
        report_content = self.format_platform_report(report_data, platform)

        draft = ReportDraft(
            finding_id=finding_id,
            platform=str(platform).lower(),
            title=report_data.get("title", "Untitled Vulnerability"),
            severity=report_data.get("severity", "Medium"),
            report_content=report_content,
            quality_score=float(quality["final_score"]),
        )

        self.db.add(draft)
        await self.db.commit()
        await self.db.refresh(draft)

        return {
            "draft_id": str(draft.id),
            "finding_id": str(finding_id),
            "platform": draft.platform,
            "severity": draft.severity,
            "quality_score": draft.quality_score,
            "quality_breakdown": quality["breakdown"],
            "weak_dimensions": quality["weak_dimensions"],
            "high_signal_tags": context.get("high_signal_tags", []),
            "human_review_required": True,
            "report_content": report_content,
        }
