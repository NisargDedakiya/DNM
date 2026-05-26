import logging
from typing import Dict, List, Any

logger = logging.getLogger(__name__)

class ReconPlanner:
    """Plans tool sequences and workflows for recon execution."""

    def build_recon_plan(self, target: str, strategy: Dict[str, Any]) -> Dict[str, Any]:
        """Construct the execution plan based on strategy."""
        logger.info(f"Building recon plan for {target}")
        
        tools = self.select_recon_tools(strategy)
        sequence = self.optimize_scan_sequence(tools)
        
        return {
            "target": target,
            "steps": sequence,
            "estimated_duration": "45m"
        }

    def select_recon_tools(self, strategy: Dict[str, Any]) -> List[str]:
        """Select appropriate advisory tools (e.g., subfinder, httpx, passive nuclei)."""
        tools = ["subfinder", "httpx"]
        if strategy.get("deep_scan"):
            tools.append("nuclei_passive")
        return tools

    def optimize_scan_sequence(self, tools: List[str]) -> List[Dict[str, str]]:
        """Order tools properly (e.g., discovery -> resolution -> analysis)."""
        sequence = []
        for i, tool in enumerate(tools):
            sequence.append({"step": i+1, "tool": tool})
        return sequence

recon_planner = ReconPlanner()
