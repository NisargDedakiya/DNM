import logging
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

class ExposureAnalyzer:
    """Detects asset drift and newly exposed attack surfaces."""

    def detect_exposure_changes(self, historical_state: Dict[str, Any], current_state: Dict[str, Any]) -> List[str]:
        """Compare graph states to find new open ports or APIs."""
        changes = []
        old_ports = set(historical_state.get("open_ports", []))
        new_ports = set(current_state.get("open_ports", []))
        
        added = new_ports - old_ports
        if added:
            changes.append(f"New ports exposed: {list(added)}")
            
        return changes

    def analyze_asset_drift(self, target: str, diff_data: Dict[str, Any]) -> bool:
        """Determine if the drift warrants an immediate targeted recon."""
        logger.info(f"Analyzing asset drift for {target}")
        if diff_data.get("new_subdomains_count", 0) > 5:
            return True
        return False

    def identify_high_risk_changes(self, changes: List[str]) -> List[str]:
        """Filter for changes that usually imply critical risk."""
        high_risk = []
        for change in changes:
            if "port 22" in change or "admin" in change:
                high_risk.append(change)
        return high_risk

exposure_analyzer = ExposureAnalyzer()
