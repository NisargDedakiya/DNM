import logging
from typing import Dict, Any, List

from backend.strategy.prioritizer import prioritizer
from backend.strategy.recon_planner import recon_planner
from backend.strategy.exposure_analyzer import exposure_analyzer

logger = logging.getLogger(__name__)

class StrategyEngine:
    """Core AI engine for autonomous hunt orchestration and planning."""

    async def generate_hunt_strategy(self, target: str, org_id: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Synthesize a complete recon strategy for a target."""
        logger.info(f"Generating hunt strategy for {target}")
        
        # In a full implementation, pass context to LLM
        strategy = {
            "focus_areas": ["auth", "graphql", "cloud_exposure"],
            "deep_scan": True,
            "risk_score": 85.0
        }
        
        # Build executable plan
        plan = recon_planner.build_recon_plan(target, strategy)
        
        return {
            "target": target,
            "strategy": strategy,
            "execution_plan": plan,
            "recommended_actions": self.recommend_next_actions(strategy)
        }

    def recommend_next_actions(self, strategy: Dict[str, Any]) -> List[str]:
        actions = ["Validate scope boundary"]
        if "auth" in strategy.get("focus_areas", []):
            actions.append("Request approval for authenticated fuzzing")
        return actions

strategy_engine = StrategyEngine()
