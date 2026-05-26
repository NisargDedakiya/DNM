import logging
from typing import Dict, List, Any

logger = logging.getLogger(__name__)

class FindingCorrelator:
    """Intelligently correlates related findings and deduplicates them."""

    def correlate_findings(self, new_finding: Dict[str, Any], existing_findings: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Find semantic and contextual relationships."""
        relationships = []
        for existing in existing_findings:
            rel_type = self.build_finding_relationships(new_finding, existing)
            if rel_type:
                relationships.append({
                    "finding_a_id": new_finding.get("id"),
                    "finding_b_id": existing.get("id"),
                    "relationship_type": rel_type
                })
        return relationships

    def detect_duplicate_patterns(self, finding_a: Dict[str, Any], finding_b: Dict[str, Any]) -> bool:
        """Intelligently detect if two findings are the same issue on different endpoints."""
        if finding_a.get("title") == finding_b.get("title"):
            if finding_a.get("target") == finding_b.get("target"):
                return True
        return False

    def build_finding_relationships(self, finding_a: Dict[str, Any], finding_b: Dict[str, Any]) -> str:
        """Determine the type of relationship based on host, tech, or parameters."""
        if self.detect_duplicate_patterns(finding_a, finding_b):
            return "same_vulnerability"
            
        if finding_a.get("target") == finding_b.get("target"):
            return "same_host"
            
        # Example: API relationship
        if "api" in finding_a.get("target", "") and "api" in finding_b.get("target", ""):
            return "api_relationship"
            
        return ""

finding_correlator = FindingCorrelator()
