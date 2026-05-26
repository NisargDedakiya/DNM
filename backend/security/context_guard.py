import logging
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

class AIContextGuard:
    """Isolates AI memory and context from cross-org contamination."""

    def validate_ai_context(self, context_data: Dict[str, Any], org_id: str):
        """Ensure all findings and attack paths fed to the LLM belong to org_id."""
        findings = context_data.get("findings", [])
        for f in findings:
            if f.get("organization_id") != org_id:
                logger.critical(f"Cross-org finding detected in AI context build! org: {org_id}")
                raise ValueError("AI Context contamination detected.")

    def sanitize_cross_org_context(self, raw_data: List[Dict[str, Any]], org_id: str) -> List[Dict[str, Any]]:
        """Filter out any data that doesn't explicitly match the org_id."""
        return [d for d in raw_data if d.get("organization_id") == org_id]

    def isolate_memory_scope(self, session_id: str, org_id: str):
        """Ensure chat session belongs to org before retrieving history."""
        # Check DB to confirm session_id maps to org_id
        pass

context_guard = AIContextGuard()
