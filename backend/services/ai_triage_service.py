import json
import logging
from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from backend.ai.claude_client import claude
from backend.core.enums import FindingSeverity
from backend.services.finding_service import FindingService
from backend.schemas.finding import FindingCreate

logger = logging.getLogger(__name__)

TRIAGE_SYSTEM = '''
You are a senior bug bounty hunter triaging security scanner output.
Classify findings using REAL exploitability — not just theoretical impact.
Only include findings with confidence >= 0.35.

Severity mapping (align to HackerOne):
critical: RCE, SQLi+extraction, ATO, auth bypass, SSRF to cloud metadata
high: Stored XSS, IDOR on sensitive data, privilege escalation, exposed creds
medium: Reflected XSS, CSRF on sensitive actions, meaningful info disclosure
low: Self-XSS, open redirect, missing headers, low-impact disclosure
info: Best practice violations, theoretical issues with no real path to exploitation

Return ONLY a JSON array. Each element:
{
  title: str,
  severity: critical|high|medium|low|info,
  cvss_score: float,
  confidence: float,
  bug_type: str,
  affected_url: str,
  description: str,
  evidence: str,
  needs_verify: bool,
  false_positive_risk: low|medium|high,
  beginner_explanation: str
}
Return [] if no real findings.
'''

# Severity string → FindingSeverity enum mapping
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
        org_id: UUID,
        context: dict,   # {scan_type, target_url, tech_stack}
        user_id: UUID | None = None,
    ) -> list:
        if not tool_output or not tool_output.strip():
            return []

        # If user_id is not provided, resolve it from the program's owner (created_by)
        if not user_id:
            from backend.models.program import Program
            stmt = select(Program.created_by).where(Program.id == program_id)
            res = await db.execute(stmt)
            user_id = res.scalars().first()
            if not user_id:
                logger.error(f"Cannot perform triage: program {program_id} has no owner user.")
                return []

        # Chunk long output — Claude context limit
        chunks = [tool_output[i:i+5000] for i in range(0, min(len(tool_output), 25000), 5000)]
        all_raw = []
        for chunk in chunks:
            prompt = (
                f'Scanner: {context.get("scan_type", "generic")} '
                f'Target: {context.get("target_url", "unknown")} '
                f'Tech stack: {context.get("tech_stack", "unknown")} '
                f'Output: {chunk}'
            )
            try:
                raw = await claude.analyze_json(prompt, TRIAGE_SYSTEM)
                if isinstance(raw, list):
                    all_raw.extend(raw)
            except Exception as e:
                logger.error(f'Triage chunk failed: {e}')

        saved = []
        for item in all_raw:
            if item.get('confidence', 0) < 0.35:
                continue
            severity = SEV_MAP.get(item.get('severity', 'info'), FindingSeverity.info)
            
            # Defensive padding/truncation for pydantic constraints
            title = item.get('title', 'Untitled Finding')
            if len(title) < 3:
                title = f"{title} - Vuln"
            title = title[:255]

            description = item.get('description', '')
            if len(description) < 10:
                description = f"Vulnerability details: {description}. Affected url: {item.get('affected_url', '')}."
            description = description[:10000]

            # Build FindingCreate — match your existing schema fields exactly
            fc = FindingCreate(
                title=title,
                severity=severity,
                description=description,
                evidence=item.get('evidence', ''),
                endpoint=item.get('affected_url', ''),
                program_id=program_id,
                scan_id=scan_id,
            )
            try:
                # Use your existing FindingService.create_finding()
                finding = await FindingService.create_finding(
                    db=db,
                    title=fc.title,
                    description=fc.description,
                    severity=fc.severity,
                    program_id=fc.program_id,
                    user_id=user_id,
                    endpoint=fc.endpoint,
                    evidence=fc.evidence,
                    scan_id=fc.scan_id,
                )
                saved.append(finding)
                # Alert on critical findings
                if severity == FindingSeverity.critical and item.get('confidence', 0) >= 0.7:
                    await self._alert(org_id, item, finding.id)
            except Exception as e:
                logger.error(f'Failed to save finding: {e}')

        logger.info(f'Triage complete: {len(saved)} findings saved from {len(all_raw)} raw')
        return saved

    async def _alert(self, org_id: UUID, item: dict, finding_id: UUID):
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
            logger.error(f'Alert publish failed: {e}')

        try:
            from backend.integrations.telegram_bot import telegram
            # Fetch program name or pass program_id placeholder/information if available
            await telegram.alert_critical(
                title=item.get('title', 'Critical Vulnerability'),
                program=f"Org {org_id}",
                severity=item.get('severity', 'critical'),
                confidence=item.get('confidence', 1.0),
                url=item.get('affected_url', 'unknown')
            )
        except Exception as e:
            logger.error(f'Telegram alert dispatch failed: {e}')


    async def detect_chains(self, db: AsyncSession, program_id: UUID) -> list[dict]:
        # Resolve owner user_id from the program table
        from backend.models.program import Program
        stmt = select(Program.created_by).where(Program.id == program_id)
        res = await db.execute(stmt)
        user_id = res.scalars().first()
        if not user_id:
            logger.error(f"Cannot perform chain detection: program {program_id} has no owner user.")
            return []

        # Load all findings for program from DB using existing FindingService
        findings_result = await FindingService.get_program_findings(
            db, program_id=program_id, user_id=user_id, limit=100
        )
        if isinstance(findings_result, tuple):
            findings = findings_result[0]
        else:
            findings = getattr(findings_result, 'findings', findings_result)

        if len(findings) < 2:
            return []

        CHAIN_SYS = '''
        Find vulnerability chains — low bugs combining into critical.
        Known chains: Open Redirect + OAuth = ATO, SSRF + metadata = creds,
        Info Disclosure + IDOR = data breach, Stored XSS + CSRF token = ATO.
        Return JSON: [{chain_name, finding_ids, steps: [str], severity_after, confidence}]
        Return [] if no chains.
        '''
        summary = [{'id': str(f.id), 'title': f.title, 'severity': str(f.severity),
                     'endpoint': f.endpoint} for f in findings]
        try:
            chains = await claude.analyze_json(json.dumps(summary), CHAIN_SYS)
            return chains if isinstance(chains, list) else []
        except Exception as e:
            logger.error(f'Chain detection failed: {e}')
            return []

ai_triage = AITriageService()
