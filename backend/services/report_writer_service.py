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
Write a professional HackerOne bug bounty report from the finding details provided.

Title format: [Severity] VulnType via /endpoint — Business impact in one phrase
Example: [Critical] SQL Injection via /api/search — Full database extraction possible

Steps to Reproduce must be exact — a stranger should reproduce in under 10 minutes.
Impact must state the REAL business consequence — not just 'XSS exists'.

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

RESCORE_SYSTEM = '''
You are a senior bug bounty triage manager. Grade the provided vulnerability report draft.

Criteria:
- Title format (0-20 points): Must match [Severity] VulnType via /endpoint — Business impact.
- Steps clarity (0-20 points): Must be clear, precise, and easily reproducible.
- Impact strength (0-20 points): Must describe realistic business consequences.
- Evidence quality (0-20 points): Clear evidence or proof-of-concept description.
- Remediation quality (0-20 points): Practical and precise remediation advice.

Return ONLY valid JSON with these fields:
{
  "quality_score": int (0 to 100),
  "quality_breakdown": {
    "title_format": int (0-20),
    "steps_clarity": int (0-20),
    "impact_strength": int (0-20),
    "evidence_quality": int (0-20),
    "remediation_quality": int (0-20)
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
            f'Evidence: {(finding.evidence or "")[:1000]} '
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
            quality_score=int(data.get('quality_score', 0)),
            quality_breakdown=data.get('quality_breakdown', {}),
            improvements=data.get('improvements', []),
        )
        db.add(report)
        await db.commit()
        await db.refresh(report)
        return report

    async def rescore(
        self,
        db: AsyncSession,
        report_id: UUID,
    ) -> Report:
        report = await db.get(Report, report_id)
        if not report:
            raise ValueError('Report not found')
        
        from backend.services.finding_service import FindingService
        finding = await FindingService.get_finding_by_id(db, report.finding_id)
        
        rescore_prompt = (
            f"Please grade the following vulnerability report draft:\n\n"
            f"Title: {report.title}\n"
            f"Platform: {report.platform}\n"
            f"Severity: {report.severity}\n"
            f"Vulnerability Type: {report.vulnerability_type}\n"
            f"Description: {report.description}\n"
            f"Steps to Reproduce: {report.steps_to_reproduce}\n"
            f"Impact: {report.impact}\n"
            f"Remediation: {report.remediation}\n"
            f"Associated scanner/evidence notes: {finding.evidence if finding else 'None'}\n"
        )
        
        data = await claude.analyze_json(rescore_prompt, RESCORE_SYSTEM)
        
        report.quality_score = int(data.get('quality_score', 0))
        report.quality_breakdown = data.get('quality_breakdown', {})
        report.improvements = data.get('improvements', [])
        
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
