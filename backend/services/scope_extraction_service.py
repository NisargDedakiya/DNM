"""
Scope Extraction Service
AI-assisted scope normalization and validation
"""
import re
import json
from typing import Dict, List, Optional, Tuple, Any
from urllib.parse import urlparse, ParseResult
import logging
from dataclasses import dataclass, asdict

from backend.ai.claude_client import ClaudeClient
from backend.core.scope_validator import ScopeValidator

logger = logging.getLogger(__name__)


@dataclass
class ScopeTarget:
    """Normalized scope target"""
    target: str  # domain.com, 192.168.1.0/24, https://api.example.com/v1/*, etc
    asset_type: str  # website, api, mobile_ios, mobile_android, cloud_service, iot, hardware, source_code
    in_scope: bool
    wildcard: bool = False
    base_domain: Optional[str] = None
    priority: Optional[str] = None
    notes: Optional[str] = None
    restrictions: Optional[Dict[str, Any]] = None
    
    def to_dict(self):
        return asdict(self)


class ScopeExtractor:
    """
    AI-assisted scope extraction from Bugcrowd engagement data
    Normalizes targets and prepares for recon integration
    """
    
    def __init__(self, claude_client: ClaudeClient, scope_validator: ScopeValidator):
        self.claude = claude_client
        self.validator = scope_validator
    
    async def extract_structured_scope(
        self,
        raw_scope_text: str,
        program_context: Optional[str] = None
    ) -> Dict[str, List[ScopeTarget]]:
        """
        Extract structured scope from raw text using AI
        
        Args:
            raw_scope_text: Raw scope text from engagement page
            program_context: Additional context about the program
            
        Returns:
            Dict with in_scope and out_of_scope lists of normalized targets
        """
        if not raw_scope_text or not raw_scope_text.strip():
            logger.warning("Empty scope text provided")
            return {"in_scope": [], "out_of_scope": []}
        
        # Prepare AI prompt
        prompt = self._build_scope_extraction_prompt(raw_scope_text, program_context)
        
        try:
            # Call Claude for structure
            response = await self.claude.query_async(
                prompt,
                temperature=0.2,  # Low temperature for deterministic output
                max_tokens=2000
            )
            
            # Parse AI response
            extracted = self._parse_ai_scope_response(response)
            
            # Normalize all targets
            result = {
                "in_scope": [],
                "out_of_scope": []
            }
            
            for target in extracted.get("in_scope", []):
                normalized = await self.normalize_scope_targets(target, in_scope=True)
                result["in_scope"].extend(normalized)
            
            for target in extracted.get("out_of_scope", []):
                normalized = await self.normalize_scope_targets(target, in_scope=False)
                result["out_of_scope"].extend(normalized)
            
            logger.info(f"Extracted {len(result['in_scope'])} in-scope and {len(result['out_of_scope'])} out-of-scope targets")
            return result
        
        except Exception as e:
            logger.error(f"Error extracting scope: {str(e)}", exc_info=True)
            return {"in_scope": [], "out_of_scope": []}
    
    def _build_scope_extraction_prompt(self, raw_text: str, context: Optional[str]) -> str:
        """Build AI prompt for scope extraction"""
        
        prompt = f"""You are a security expert extracting scope from bug bounty program text.

IMPORTANT: You MUST ONLY extract targets that are explicitly stated. DO NOT invent, assume, or fabricate targets.

Program context:
{context or "General bug bounty program"}

Raw scope text:
---
{raw_text}
---

Extract all targets mentioned in the scope text. Return valid JSON with this structure:
{{
  "in_scope": [
    {{
      "target": "domain.com or IP or URL pattern",
      "type": "website | api | mobile_ios | mobile_android | cloud_service | iot | hardware | source_code",
      "wildcard": true/false,
      "notes": "any specific restrictions mentioned"
    }}
  ],
  "out_of_scope": [
    {{
      "target": "excluded domain or IP",
      "type": "website | api | mobile_ios | mobile_android | cloud_service | iot | hardware | source_code",
      "notes": "reason for exclusion if mentioned"
    }}
  ]
}}

Rules:
1. Extract ONLY targets explicitly mentioned
2. Include subdomains marked as in-scope (e.g., "*.domain.com")
3. Include IP ranges if mentioned (e.g., "192.168.1.0/24")
4. Include API endpoints if mentioned (e.g., "https://api.example.com/v1/*")
5. Do NOT invent or assume targets
6. Mark wildcards appropriately
7. Return valid JSON only, no additional text

Return only the JSON object, no markdown formatting or additional text."""
        
        return prompt
    
    def _parse_ai_scope_response(self, response: str) -> Dict[str, List[Dict[str, Any]]]:
        """Parse JSON response from Claude"""
        try:
            # Extract JSON from response
            json_match = re.search(r"\{[\s\S]*\}", response)
            if not json_match:
                logger.warning("No JSON found in Claude response")
                return {"in_scope": [], "out_of_scope": []}
            
            data = json.loads(json_match.group())
            return data
        
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Claude response as JSON: {str(e)}")
            return {"in_scope": [], "out_of_scope": []}
    
    async def normalize_scope_targets(
        self,
        target_str: str,
        in_scope: bool = True
    ) -> List[ScopeTarget]:
        """
        Normalize a scope target string to structured format
        
        Args:
            target_str: Raw target string
            in_scope: Whether target is in or out of scope
            
        Returns:
            List of ScopeTarget objects
        """
        targets = []
        
        # Clean the target
        target_str = target_str.strip()
        if not target_str:
            return targets
        
        # Split multiple targets on common delimiters
        targets_to_process = re.split(r'[,;\n]', target_str)
        
        for target in targets_to_process:
            target = target.strip()
            if not target or len(target) < 2:
                continue
            
            # Detect type and normalize
            asset_type = self._detect_asset_type(target)
            normalized, is_wildcard = self._normalize_target(target)
            
            # Extract base domain for websites
            base_domain = self._extract_base_domain(normalized) if asset_type == "website" else None
            
            # Validate
            is_valid = await self.validate_scope_entries([normalized])
            
            scope_target = ScopeTarget(
                target=normalized,
                asset_type=asset_type,
                in_scope=in_scope,
                wildcard=is_wildcard,
                base_domain=base_domain,
                priority=self._determine_priority(normalized, asset_type),
                restrictions=self._extract_restrictions(target)
            )
            
            targets.append(scope_target)
        
        return targets
    
    def _detect_asset_type(self, target: str) -> str:
        """Detect asset type from target string"""
        target_lower = target.lower()
        
        # API detection
        if any(keyword in target_lower for keyword in ["api.", "/api", "graphql", "webhook", "rest"]):
            return "api"
        
        # Mobile detection
        if any(keyword in target_lower for keyword in ["ios", "iphone", "app store", "play store"]):
            return "mobile_ios"
        if any(keyword in target_lower for keyword in ["android", "play store"]):
            return "mobile_android"
        
        # Cloud detection
        if any(keyword in target_lower for keyword in ["aws", "azure", "gcp", "s3", "storage", "cdn"]):
            return "cloud_service"
        
        # IoT detection
        if any(keyword in target_lower for keyword in ["iot", "mqtt", "device", "sensor"]):
            return "iot_device"
        
        # Hardware detection
        if any(keyword in target_lower for keyword in ["hardware", "device", "router", "switch"]):
            return "hardware"
        
        # Source code detection
        if any(keyword in target_lower for keyword in ["github", "gitlab", "repository", "source"]):
            return "source_code"
        
        # Website (default)
        return "website"
    
    def _normalize_target(self, target: str) -> Tuple[str, bool]:
        """
        Normalize target to canonical form
        
        Returns:
            (normalized_target, is_wildcard)
        """
        target = target.strip()
        is_wildcard = False
        
        # Detect and preserve wildcards
        if target.startswith("*."):
            is_wildcard = True
            # Extract base domain
            base = target[2:]
            target = base
        
        # Remove common prefixes
        target = re.sub(r"^(https?://)", "", target, flags=re.IGNORECASE)
        target = re.sub(r"^www\.", "", target, flags=re.IGNORECASE)
        
        # Normalize trailing slashes
        target = target.rstrip("/")
        
        # Normalize IP ranges
        if "/" in target and self._is_ip_range(target):
            # Valid CIDR notation
            pass
        
        # If it looks like an IP without range, leave as-is
        # If it looks like a domain, ensure lowercase
        if not self._is_ip_address(target):
            target = target.lower()
        
        # Re-add wildcard marker
        if is_wildcard:
            target = f"*.{target}"
        
        return target, is_wildcard
    
    def _is_ip_address(self, target: str) -> bool:
        """Check if target is an IP address or range"""
        # Remove wildcard for check
        check_target = target.replace("*.", "")
        
        # Simple IP pattern
        ip_pattern = r"^(\d{1,3}\.){3}\d{1,3}(/\d{1,2})?$"
        return bool(re.match(ip_pattern, check_target))
    
    def _is_ip_range(self, target: str) -> bool:
        """Check if target is a valid CIDR range"""
        ip_pattern = r"^(\d{1,3}\.){3}\d{1,3}/\d{1,2}$"
        return bool(re.match(ip_pattern, target))
    
    def _extract_base_domain(self, target: str) -> Optional[str]:
        """Extract base domain from target"""
        # Remove wildcard
        target = target.replace("*.", "")
        
        # Remove protocol
        target = re.sub(r"^https?://", "", target)
        
        # Remove path
        target = target.split("/")[0]
        
        # Remove port
        target = target.split(":")[0]
        
        # Get last two parts for base domain (simple heuristic)
        parts = target.split(".")
        if len(parts) >= 2:
            return ".".join(parts[-2:])
        
        return target
    
    def _determine_priority(self, target: str, asset_type: str) -> Optional[str]:
        """Determine priority level for target"""
        target_lower = target.lower()
        
        # High priority: APIs, public endpoints
        if asset_type == "api" or "/api" in target_lower:
            return "high"
        
        # High priority: admin panels
        if any(keyword in target_lower for keyword in ["admin", "manage", "panel"]):
            return "high"
        
        # Medium priority: main domains
        if asset_type == "website" and target_lower.count(".") <= 1:
            return "medium"
        
        # Low priority: staging/dev environments
        if any(keyword in target_lower for keyword in ["staging", "dev", "test", "qa"]):
            return "low"
        
        return None
    
    def _extract_restrictions(self, target: str) -> Optional[Dict[str, Any]]:
        """Extract any restrictions mentioned for target"""
        restrictions = {}
        target_lower = target.lower()
        
        # Rate limit detection
        if "rate limit" in target_lower or "ratelimit" in target_lower:
            restrictions["rate_limited"] = True
        
        # Time restriction detection
        if "business hours" in target_lower or "9-5" in target_lower:
            restrictions["business_hours_only"] = True
        
        # Endpoint exclusion
        if "no " in target_lower:
            restrictions["has_exclusions"] = True
        
        return restrictions if restrictions else None
    
    async def validate_scope_entries(self, targets: List[str]) -> bool:
        """
        Validate targets using scope validator
        
        Args:
            targets: List of normalized targets
            
        Returns:
            True if all targets are valid
        """
        for target in targets:
            try:
                # Use existing scope validator
                is_valid = self.validator.validate_target(target)
                if not is_valid:
                    logger.warning(f"Target failed validation: {target}")
                    return False
            except Exception as e:
                logger.error(f"Error validating target {target}: {str(e)}")
                return False
        
        return True
