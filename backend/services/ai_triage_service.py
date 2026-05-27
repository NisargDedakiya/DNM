import json
import logging
from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from backend.ai.claude_client import claude, ClaudeAPIError
from backend.core.enums import FindingSeverity
from backend.services.finding_service import FindingService
from backend.schemas.finding import FindingCreate

logger = logging.getLogger(__name__)

TRIAGE_SYSTEM = '''
You are a senior bug bounty hunter triaging security scanner output.
Classify findings using REAL exploitability — not just theoretical impact.
Only report findings with confidence >= 0.35.

SEVERITY GUIDE (match HackerOne severity labels):
critical = RCE, SQLi+data extraction, ATO, auth bypass, SSRF to cloud metadata
high = Stored XSS, IDOR on sensitive data, privilege escalation, exposed credentials
medium = Reflected XSS, CSRF on sensitive actions, meaningful info disclosure
low = Self-XSS, open redirect, missing security headers, low-impact disclosure
info = Best practice, theoretical with no real exploitation path

Return ONLY a JSON array. Each element has:
{
  "title": "str",
  "severity": "critical|high|medium|low|info",
  "cvss_score": 0.0,
  "confidence": 0.0,
  "bug_type": "str",
  "affected_url": "str",
  "description": "str",
  "evidence": "str",
  "needs_manual_verify": true,
  "false_positive_risk": "low|medium|high",
  "beginner_explanation": "str"
}
Return [] if no real findings exist in the output.
'''

SEV_MAP = {
    'critical': FindingSeverity.critical,
    'high':     FindingSeverity.high,
    'medium':   FindingSeverity.medium,
    'low':      FindingSeverity.low,
    'info':     FindingSeverity.info,
}

class AITriageService:

    async def triage(
        self,
        db: AsyncSession,
        tool_output: str,
        scan_id: UUID,
        program_id: UUID,
        organization_id: UUID,
        context: dict,
        created_by_id: UUID | None = None,
    ) -> list:
        if not tool_output or not tool_output.strip():
            return []

        # If created_by_id is not provided, resolve it from the program's owner
        if not created_by_id:
            from backend.models.program import Program
            stmt = select(Program.created_by).where(Program.id == program_id)
            res = await db.execute(stmt)
            created_by_id = res.scalars().first()
            if not created_by_id:
                logger.error(f"Cannot perform triage: program {program_id} has no owner user.")
                return []

        # Process in 5000-char chunks to stay within Claude context
        chunks = [tool_output[i:i+5000] for i in range(0, min(len(tool_output), 30000), 5000)]
        raw_findings: list[dict] = []
        for chunk in chunks:
            prompt = (
                f'Scanner type: {context.get("scan_type", "generic")} '
                f'Target URL: {context.get("target_url", "unknown")} '
                f'Tech stack detected: {context.get("tech_stack", "unknown")} '
                f'Raw scanner output: {chunk}'
            )
            try:
                result = await claude.analyze_json(prompt, TRIAGE_SYSTEM)
                if isinstance(result, list):
                    raw_findings.extend(result)
            except ClaudeAPIError as e:
                logger.error(f'Triage chunk failed: {e}')

        saved = []
        for item in raw_findings:
            if float(item.get('confidence', 0)) < 0.35:
                continue
            severity = SEV_MAP.get(item.get('severity', 'info'), FindingSeverity.info)
            
            title = item.get('title', 'Untitled Finding')
            if len(title) < 3:
                title = f"{title} - Vuln"
            title = title[:255]

            description = item.get('description', '')
            if len(description) < 10:
                description = f"Vulnerability details: {description}. Affected URL: {item.get('affected_url', '')}."
            description = description[:10000]

            try:
                fc = FindingCreate(
                    title=title,
                    severity=severity,
                    description=description,
                    evidence=item.get('evidence', '')[:50000],
                    endpoint=item.get('affected_url', '')[:2048],
                    program_id=program_id,
                    scan_id=scan_id,
                )
                
                finding = await FindingService.create_finding(
                    db,
                    title=fc.title,
                    description=fc.description,
                    severity=fc.severity,
                    program_id=fc.program_id,
                    user_id=created_by_id,
                    endpoint=fc.endpoint,
                    evidence=fc.evidence,
                    scan_id=fc.scan_id,
                )
                saved.append(finding)
                
                # Alert on critical + high confidence findings
                if severity == FindingSeverity.critical and float(item.get('confidence', 0)) >= 0.7:
                    await self._publish_alert(organization_id, item, finding.id)
            except Exception as e:
                logger.error(f'Failed to save triaged finding: {e}')

        logger.info(f'Triage complete: {len(saved)}/{len(raw_findings)} findings saved')
        return saved

    async def _publish_alert(self, org_id: UUID, item: dict, finding_id: UUID):
        try:
            from backend.core.redis import get_redis
            redis = await get_redis()
            await redis.publish(f'alerts:{org_id}', json.dumps({
                'event': 'critical_finding',
                'finding_id': str(finding_id),
                'title': item.get('title'),
                'severity': item.get('severity'),
                'confidence': item.get('confidence'),
                'url': item.get('affected_url', ''),
            }))
        except Exception as e:
            logger.error(f'Alert publish failed (non-fatal): {e}')

    async def detect_chains(self, db: AsyncSession, program_id: UUID) -> list[dict]:
        # Resolve owner user_id from the program table
        from backend.models.program import Program
        stmt = select(Program.created_by).where(Program.id == program_id)
        res = await db.execute(stmt)
        user_id = res.scalars().first()
        if not user_id:
            logger.error(f"Cannot perform chain detection: program {program_id} has no owner user.")
            return []

        # Load all findings for this program
        findings_result = await FindingService.get_program_findings(
            db, program_id=program_id, user_id=user_id, limit=100
        )
        findings = getattr(findings_result, 'findings', findings_result)
        if isinstance(findings_result, tuple):
            findings = findings_result[0]
        else:
            findings = getattr(findings_result, 'findings', findings_result)

        if not findings or len(findings) < 2:
            return []

        CHAIN_SYS = '''
        Find vulnerability chains — lower-severity bugs combining into critical.
        Known valuable chains:
        - Open Redirect + OAuth flow = Account Takeover (critical)
        - SSRF + AWS metadata endpoint = Cloud credentials (critical)
        - Info Disclosure (user IDs) + IDOR = Mass data breach (critical)
        - Stored XSS + CSRF token in DOM = Account Takeover (critical)
        Return JSON array of chains, or [] if none exist.
        Format: [{chain_name, finding_ids: [str], steps: [str], severity_after: str, confidence: float}]
        '''
        summary = [
            {'id': str(f.id), 'title': f.title,
             'severity': str(f.severity), 'url': f.endpoint}
            for f in findings
        ]
        try:
            chains = await claude.analyze_json(json.dumps(summary), CHAIN_SYS)
            return chains if isinstance(chains, list) else []
        except Exception as e:
            logger.error(f'Chain detection failed: {e}')
            return []

# Singleton
ai_triage = AITriageService()
