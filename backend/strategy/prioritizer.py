import logging
from typing import Dict, List, Any

logger = logging.getLogger(__name__)

class Prioritizer:
    """Scores and prioritizes assets based on risk factors."""

    def score_target(self, target_data: Dict[str, Any]) -> float:
        """Calculate a risk score based on various factors."""
        score = 10.0
        
        # Factor 1: Internet exposure
        if target_data.get("is_internet_facing"):
            score += 20.0
            
        # Factor 2: Auth systems
        if target_data.get("has_auth_interface"):
            score += 30.0
            
        # Factor 3: Blast radius (from graph)
        blast_radius = target_data.get("blast_radius", "low")
        if blast_radius == "high_lateral_movement":
            score += 40.0
            
        return min(score, 100.0)

    def prioritize_recon_targets(self, targets: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Sort a list of targets by their computed risk score."""
        for target in targets:
            target["priority_score"] = self.score_target(target)
            
        # Sort descending by priority_score
        return sorted(targets, key=lambda x: x.get("priority_score", 0), reverse=True)

prioritizer = Prioritizer()
