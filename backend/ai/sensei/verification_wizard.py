from backend.ai.claude_client import claude
from backend.services.finding_service import FindingService
import logging
logger = logging.getLogger(__name__)

VERIFY_SYS = '''
Create an exact verification recipe for a security finding.
Be extremely specific: exact URLs, exact payloads, exact indicators.
Return ONLY valid JSON:
{
  summary: str,
  is_worth_verifying: bool,
  difficulty: beginner|intermediate|advanced,
  estimated_minutes: int,
  tools_needed: [str],
  verification_steps: [{
    step_number: int,
    action: str,
    payload_to_copy: str,
    where_to_inject: str,
    expected_if_real: str,
    expected_if_false_positive: str,
    screenshot_this: bool
  }],
  confirmed_indicators: [str],
  false_positive_signs: [str],
  severity_if_confirmed: str,
  bounty_estimate: str
}
'''

class VerificationWizard:
    async def generate(self, db, finding_id) -> dict:
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
