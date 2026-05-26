from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from backend.ai.claude_client import claude

VERIFY_SYS = '''
Create an exact verification recipe for a security finding.
Be specific: exact URLs, exact payloads, exact success indicators.
Write as if guiding someone doing this for the first time.
Return ONLY valid JSON:
{
  "summary": "str",
  "is_worth_verifying": true,
  "difficulty": "beginner|intermediate|advanced",
  "estimated_minutes": 10,
  "tools_needed": ["str"],
  "verification_steps": [{
    "step_number": 1,
    "action": "str",
    "payload_to_copy": "str",
    "where_to_inject": "str",
    "expected_if_real": "str",
    "expected_if_false_positive": "str",
    "screenshot_this": true
  }],
  "confirmed_indicators": ["str"],
  "false_positive_signs": ["str"],
  "severity_if_confirmed": "str",
  "bounty_estimate": "str"
}
'''

class VerificationWizard:
    async def generate(self, db: AsyncSession, finding_id: UUID) -> dict:
        from backend.services.finding_service import FindingService
        finding = await FindingService.get_finding_by_id(db, finding_id)
        if not finding:
            raise ValueError('Finding not found')
        prompt = (
            f'Finding: {finding.title} '
            f'Severity: {finding.severity} '
            f'URL: {finding.endpoint or "unknown"} '
            f'Evidence: {(finding.evidence or "")[:400]} '
            f'Bug type: {getattr(finding, "bug_type", "unknown")}'
        )
        return await claude.analyze_json(prompt, VERIFY_SYS)

verification_wizard = VerificationWizard()
