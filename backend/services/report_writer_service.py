import json
import logging
from uuid import UUID
from datetime import datetime, timezone
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from backend.ai.claude_client import claude
from backend.models.report import Report
from backend.models.finding import Finding
from backend.models.program import Program

logger = logging.getLogger(__name__)

REPORT_SYSTEM = '''
Write a professional HackerOne bug bounty report.
Title format: [Severity] VulnType in /path — Business impact
Steps must be exact — reproducible by a stranger in 10 minutes.
Impact must state real business consequence, not just technical description.

Return ONLY valid JSON:
{
  "title": str,
  "severity": "none"|"low"|"medium"|"high"|"critical",
  "vulnerability_type": str,
  "description": str,
  "steps_to_reproduce": [str],
  "impact": str,
  "remediation": str,
  "cvss_score": float,
  "cvss_vector": str,
  "quality_score": int,
  "quality_breakdown": {
    "title_format": int,
    "steps_clarity": int,
    "impact_strength": int,
    "evidence_quality": int,
    "remediation_quality": int
  },
  "improvements": [str]
}
'''

class ReportWriterService:

    async def generate(
        self,
        db: AsyncSession,
        finding_id: UUID,
        evidence_notes: str = '',
        platform: str = 'hackerone',
    ) -> Report:
        from backend.services.finding_service import FindingService
        finding = await FindingService.get_finding_by_id(db, finding_id)
        if not finding:
            raise ValueError('Finding not found')

        prompt = (
            f'Bug type: {getattr(finding, "bug_type", "Security Vulnerability")} '
            f'Severity: {finding.severity} '
            f'Endpoint: {finding.endpoint or "Unknown"} '
            f'Description: {finding.description} '
            f'Evidence: {finding.evidence or "See description"} '
            f'Additional notes: {evidence_notes} '
            f'Platform: {platform}'
        )

        data = await claude.analyze_json(prompt, REPORT_SYSTEM)

        # Create Report record
        report = Report(
            finding_id=finding_id,
            platform=platform,
            title=data.get('title', ''),
            severity=data.get('severity', 'medium'),
            vulnerability_type=data.get('vulnerability_type', ''),
            description=data.get('description', ''),
            steps_to_reproduce=data.get('steps_to_reproduce', []),
            impact=data.get('impact', ''),
            remediation=data.get('remediation', ''),
            cvss_score=data.get('cvss_score'),
            quality_score=data.get('quality_score', 0),
            quality_breakdown=data.get('quality_breakdown', {}),
        )
        db.add(report)
        await db.commit()
        await db.refresh(report)
        return report

    async def submit_to_hackerone(
        self, db: AsyncSession, report_id: UUID, program_handle: str
    ) -> str:
        report = await db.get(Report, report_id)
        if not report:
            raise ValueError('Report not found')
        if report.quality_score < 70:
            raise ValueError(f'Quality {report.quality_score}/100 below minimum 70')
        from backend.auth.hackerone import h1_client
        result = await h1_client.submit_report(program_handle, {
            'title': report.title,
            'severity': report.severity,
            'description': report.description,
            'steps_to_reproduce': report.steps_to_reproduce,
            'impact': report.impact,
            'remediation': report.remediation,
        })
        report.submitted_at = datetime.now(timezone.utc)
        report.platform_submission_id = result.get('submission_id', '')
        await db.commit()
        return result.get('submission_id', '')

report_writer = ReportWriterService()
