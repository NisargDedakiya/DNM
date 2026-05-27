from sqlalchemy import select
from backend.models.asset import Asset
from backend.models.endpoint import Endpoint
from backend.models.technology import Technology
from backend.models.exposure import AssetFingerprint
from backend.ai.claude_client import claude
import logging
logger = logging.getLogger(__name__)

GUIDE_SYS = '''
Generate a precise manual attack guide for a specific bug type.
Use the actual tech stack — craft payloads for the specific technology.
Return ONLY valid JSON:
{
  overview: str,
  difficulty: beginner|intermediate|advanced,
  estimated_minutes: int,
  tools: [{name: str, setup: str}],
  setup_steps: [str],
  endpoints_to_test: [{url: str, why: str, priority: int}],
  steps: [{
    step_number: int,
    action: str,
    payload: str,
    inject_location: str,
    success_indicator: str,
    false_positive: str
  }],
  waf_bypass_notes: str,
  common_pitfalls: [str],
  report_title_template: str
}
'''

SUPPORTED_BUG_TYPES = [
    'dom_xss', 'stored_xss', 'reflected_xss', 'blind_xss',
    'sql_injection', 'blind_sqli', 'nosql_injection', 'command_injection',
    'http_request_smuggling', 'ssrf', 'blind_ssrf', 'xxe',
    'ssti', 'insecure_deserialization', 'cache_poisoning',
    'idor', 'mass_assignment', 'oauth_bypass', 'jwt_confusion',
    'file_upload_bypass', 'path_traversal', 'cors_misconfiguration',
    'race_condition', 'graphql_attack', 'prototype_pollution',
    'host_header_injection', 'saml_bypass', 'ldap_injection',
]

class ManualGuide:
    async def generate(self, db, bug_type: str, program_id) -> dict:
        if bug_type not in SUPPORTED_BUG_TYPES:
            raise ValueError(f'Unsupported bug type. Choose from: {SUPPORTED_BUG_TYPES}')
        
        # Load program context from DB — get tech_stack and live endpoints
        stmt = select(Asset).where(Asset.program_id == program_id)
        res = await db.execute(stmt)
        assets = res.scalars().all()
        asset_ids = [a.id for a in assets]
        
        tech_set = set()
        endpoints = []
        if asset_ids:
            # Load technologies
            tech_stmt = select(Technology).where(Technology.asset_id.in_(asset_ids))
            tech_res = await db.execute(tech_stmt)
            techs = tech_res.scalars().all()
            for t in techs:
                if t.name:
                    tech_set.add(f"{t.name} (version: {t.version or 'unknown'})")
            
            # Load framework fingerprints
            fp_stmt = select(AssetFingerprint).where(AssetFingerprint.asset_id.in_(asset_ids))
            fp_res = await db.execute(fp_stmt)
            fps = fp_res.scalars().all()
            for fp in fps:
                if fp.detected_framework:
                    tech_set.add(fp.detected_framework)
                if fp.detected_server:
                    tech_set.add(fp.detected_server)
                if fp.detected_cms:
                    tech_set.add(fp.detected_cms)

            # Load top 30 live endpoints from DB
            ep_stmt = select(Endpoint).where(Endpoint.asset_id.in_(asset_ids)).limit(30)
            ep_res = await db.execute(ep_stmt)
            eps = ep_res.scalars().all()
            endpoints = [f"{e.method} {e.path} (status: {e.status_code})" for e in eps]

        tech_stack = ", ".join(tech_set) if tech_set else "unknown"
        endpoints_str = ", ".join(endpoints) if endpoints else "unknown"

        prompt = (
            f'Bug type to test: {bug_type} '
            f'Tech stack: {tech_stack} '
            f'Discovered endpoints: {endpoints_str}'
        )
        return await claude.analyze_json(prompt, GUIDE_SYS)

manual_guide = ManualGuide()
