import logging
from typing import Dict, List, Any
from backend.intelligence.chain_detector import chain_detector
from backend.intelligence.finding_correlator import finding_correlator
from backend.core.events import EventType
from backend.services.event_service import event_service

logger = logging.getLogger(__name__)

class ChainService:
    """Orchestrates chain detection and integrates intelligence."""

    async def run_chain_analysis(self, org_id: str, new_finding: Dict[str, Any], existing_findings: List[Dict[str, Any]]):
        """Execute the full correlation and chain detection pipeline."""
        logger.info(f"Running chain analysis for finding {new_finding.get('id')}")
        
        # 1. Correlate
        relationships = finding_correlator.correlate_findings(new_finding, existing_findings)
        
        # 2. Detect Chains
        all_findings = [new_finding] + existing_findings
        chains = chain_detector.detect_attack_chains(all_findings)
        
        if chains:
            await self.prioritize_attack_chains(org_id, chains)
            
        return {"relationships": relationships, "chains_detected": len(chains)}

    async def prioritize_attack_chains(self, org_id: str, chains: List[Dict[str, Any]]):
        """Prioritize chains and emit alerts for high-risk ones."""
        for chain in chains:
            if chain.get("severity") in ["CRITICAL", "HIGH"]:
                logger.warning(f"High-risk chain identified: {chain.get('chain_name')}")
                
                # Emit Redis Alert for realtime UI
                await event_service.emit_event(
                    EventType.FINDING_P1_ALERT,
                    org_id,
                    {"chain": chain, "message": f"Critical chain detected: {chain.get('chain_name')}"}
                )

    def generate_chain_summary(self, chain_id: str) -> str:
        """Create a human-readable summary of the attack chain."""
        return "Advisory summary: Attacker may use SSRF to reach internal metadata endpoint."

chain_service = ChainService()
