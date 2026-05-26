import logging
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

class ContextBuilder:
    """Gathers context to feed into the AI Copilot."""

    async def build_hunt_context(self, org_id: str, query: str) -> Dict[str, Any]:
        """Aggregate all relevant contextual layers for a query."""
        logger.info(f"Building hunt context for org {org_id}")
        return {
            "findings": await self.collect_related_findings(org_id, query),
            "attack_paths": await self.collect_attack_paths(org_id, query),
            "exposures": await self.collect_exposure_context(org_id, query)
        }

    async def collect_related_findings(self, org_id: str, query: str) -> List[Dict[str, Any]]:
        """Retrieve recent or query-relevant findings."""
        # Advisory: In reality, do a semantic search or DB filter
        return [{"id": "fnd_1", "title": "Exposed Graphql API", "severity": "HIGH"}]

    async def collect_attack_paths(self, org_id: str, query: str) -> List[Dict[str, Any]]:
        """Retrieve relevant attack graphs."""
        return [{"path": "GraphQL -> Sensitive User Data", "risk": "High"}]

    async def collect_exposure_context(self, org_id: str, query: str) -> Dict[str, Any]:
        """Retrieve infrastructure exposure."""
        return {"open_ports": [80, 443, 8080], "cloud_provider": "AWS"}

context_builder = ContextBuilder()
