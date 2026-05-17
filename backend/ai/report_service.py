"""
AI report generation service.

Generates markdown bug-bounty style reports for findings and persists them.
"""
from __future__ import annotations

import logging
import json
from typing import List
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from backend.ai import client, prompts
from backend.models.report import Report

logger = logging.getLogger(__name__)


async def generate_bug_bounty_report(title: str, severity: str, description: str, endpoint: str | None, evidence: str | None) -> str:
    prompt = prompts.render_report_prompt(
        title=title,
        severity=severity or "",
        description=description or "",
        endpoint=endpoint or "",
        evidence=evidence or "",
    )

    try:
        resp = await client.generate_report(prompt)
    except Exception:
        logger.exception("AI report generation failed")
        return "# Report generation failed\nPlease perform manual triage."

    # extract textual completion
    if isinstance(resp, dict):
        text = resp.get("completion") or resp.get("text") or resp.get("output") or json.dumps(resp)
    else:
        text = str(resp)

    return text


async def generate_summary(finding_ids: List[UUID], db: AsyncSession, user_id: UUID) -> List[Report]:
    """Generate and persist reports for each finding id after ownership validated."""
    from backend.models.finding import Finding

    reports: List[Report] = []
    for fid in finding_ids:
        result = await db.execute(select := __import__("sqlalchemy").select(Finding).where(Finding.id == fid))
        finding = result.scalars().first()
        if not finding:
            continue
        # ensure ownership via program
        if not finding.program or str(finding.program.created_by) != str(user_id):
            continue

        content = await generate_bug_bounty_report(
            title=finding.title,
            severity=finding.severity.value if hasattr(finding.severity, "value") else str(finding.severity),
            description=finding.description,
            endpoint=finding.endpoint or "",
            evidence=finding.evidence or "",
        )

        report = Report(finding_id=finding.id, created_by_id=user_id, generated_by_ai=True, content=content)
        db.add(report)
        await db.flush()
        reports.append(report)

    return reports
