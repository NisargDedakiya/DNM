"""
Scope Sync Service: normalizes and validates imported bug bounty scopes.
Ensures compatibility with the internal scope engine.
"""
import logging
from typing import Any, Dict, List
import re

logger = logging.getLogger(__name__)

class ScopeSyncService:
    
    @staticmethod
    def normalize_scope_targets(platform: str, raw_scopes: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """Normalize raw platform scopes into standard format."""
        normalized = {
            "in_scope": [],
            "out_of_scope": []
        }
        
        if platform == "hackerone":
            for scope in raw_scopes:
                attrs = scope.get("attributes", {})
                target = attrs.get("asset_identifier", "")
                target_type_raw = attrs.get("asset_type", "other")
                instruction = attrs.get("instruction", "")
                max_sev = attrs.get("max_severity", "none")
                eligible = attrs.get("eligible_for_bounty", False)
                
                # Normalize target type
                target_type = "other"
                if target_type_raw in ("URL", "WILDCARD"):
                    target_type = "url"
                elif target_type_raw == "CIDR":
                    target_type = "cidr"
                elif target_type_raw in ("APPLE_STORE_APP_ID", "GOOGLE_PLAY_APP_ID"):
                    target_type = "mobile"
                elif target_type_raw == "HARDWARE":
                    target_type = "hardware"
                elif target_type_raw == "SOURCE_CODE":
                    target_type = "source_code"
                    
                entry = {
                    "target": target,
                    "target_type": target_type,
                    "instruction": instruction,
                    "max_severity": max_sev
                }
                
                if eligible:
                    normalized["in_scope"].append(entry)
                else:
                    normalized["out_of_scope"].append(entry)
                    
        elif platform == "bugcrowd":
            # Placeholder for bugcrowd normalization
            pass
            
        return normalized

    @staticmethod
    def validate_imported_scope(normalized_scope: Dict[str, List[Dict[str, Any]]]) -> bool:
        """Validate that the normalized scope contains well-formed targets."""
        # Check basic structure
        if "in_scope" not in normalized_scope or "out_of_scope" not in normalized_scope:
            return False
            
        for item in normalized_scope["in_scope"] + normalized_scope["out_of_scope"]:
            if not item.get("target"):
                return False
            # Basic validation logic (can be expanded)
            target = item.get("target", "")
            if item.get("target_type") == "url":
                # Ensure no spaces, very basic check
                if " " in target:
                    return False
                    
        return True

    @staticmethod
    def merge_scope_changes(old_scope: Dict[str, Any], new_scope: Dict[str, Any]) -> Dict[str, Any]:
        """Merge old and new scopes, detecting drift."""
        # Simple replacement for now, complex diffing can be added later
        return new_scope
