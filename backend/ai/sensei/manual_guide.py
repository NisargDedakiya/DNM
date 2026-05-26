from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from backend.ai.claude_client import claude

BUG_TYPES = [
    'dom_xss', 'stored_xss', 'reflected_xss', 'blind_xss',
    'sql_injection', 'blind_sqli', 'nosql_injection', 'command_injection',
    'http_request_smuggling', 'ssrf', 'blind_ssrf', 'xxe',
    'ssti', 'insecure_deserialization', 'cache_poisoning',
    'idor', 'mass_assignment', 'oauth_bypass', 'jwt_confusion',
    'file_upload_bypass', 'path_traversal', 'cors_misconfiguration',
    'race_condition', 'graphql_depth_attack', 'prototype_pollution',
    'host_header_injection', 'saml_bypass', 'ldap_injection',
]

GUIDE_SYS = '''
Generate a precise manual attack guide for a specific bug type.
Use the actual tech stack — never generic payloads if specific ones exist.
Return ONLY valid JSON:
{
  "overview": "str",
  "difficulty": "beginner|intermediate|advanced",
  "estimated_minutes": 15,
  "tools": [{"name": "str", "setup": "str"}],
  "setup_steps": ["str"],
  "endpoints_to_test": [{"url": "str", "why": "str", "priority": 1}],
  "steps": [{
    "step_number": 1,
    "action": "str",
    "payload": "str",
    "inject_location": "str",
    "success_indicator": "str",
    "false_positive": "str"
  }],
  "waf_bypass": "str",
  "pitfalls": ["str"],
  "report_title_template": "str"
}
'''

class ManualGuide:
    async def generate(
        self, db: AsyncSession, bug_type: str, program_id: UUID
    ) -> dict:
        if bug_type not in BUG_TYPES:
            raise ValueError(f'Unsupported: {bug_type}. Choose from: {BUG_TYPES}')
            
        # Load program tech stack and live endpoints from DB
        from backend.models.asset import Asset
        from backend.models.endpoint import Endpoint
        from backend.models.technology import Technology
        
        # Load technologies
        tech_stmt = (
            select(Technology.name)
            .join(Technology.asset)
            .where(Asset.program_id == program_id)
            .distinct()
            .limit(20)
        )
        tech_res = await db.execute(tech_stmt)
        tech_stack = [row[0] for row in tech_res.all()]
        tech_stack_str = ", ".join(tech_stack) if tech_stack else "unknown"
        
        # Load top 30 endpoints
        endpoint_stmt = (
            select(Endpoint.path, Endpoint.method)
            .join(Endpoint.asset)
            .where(Asset.program_id == program_id)
            .distinct()
            .limit(30)
        )
        endpoint_res = await db.execute(endpoint_stmt)
        endpoints = [f"{method} {path}" for path, method in endpoint_res.all()]
        endpoints_str = ", ".join(endpoints) if endpoints else "none discovered"
        
        prompt = (
            f'Bug type: {bug_type} '
            f'Tech stack: {tech_stack_str} '
            f'Live endpoints: {endpoints_str} '
            f'Program ID: {program_id}'
        )
        return await claude.analyze_json(prompt, GUIDE_SYS)

manual_guide = ManualGuide()
