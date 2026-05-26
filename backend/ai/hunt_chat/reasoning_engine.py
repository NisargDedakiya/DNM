import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

class ReasoningEngine:
    """Provides advisory explanations for vulnerabilities and chains."""

    def explain_finding(self, finding: Dict[str, Any]) -> str:
        title = finding.get("title", "Unknown")
        logger.info(f"Generating reasoning for finding: {title}")
        return f"This {title} finding indicates a potential flaw in how input is processed, allowing advisory-level insight."

    def explain_attack_chain(self, chain: Dict[str, Any]) -> str:
        name = chain.get("name", "Unknown Chain")
        return f"The attack chain '{name}' suggests that an attacker could string these advisory vulnerabilities together to achieve privilege escalation."

    def explain_business_risk(self, exposure_data: Dict[str, Any]) -> str:
        return "Business risk is elevated due to the exposure of authentication mechanisms on the perimeter."

reasoning_engine = ReasoningEngine()
