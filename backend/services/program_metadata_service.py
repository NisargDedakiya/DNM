"""
Program Metadata Service
Extracts bounty metadata, auth requirements, asset classifications, and rules
"""
import json
import re
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
import logging

from backend.ai.claude_client import ClaudeClient

logger = logging.getLogger(__name__)


@dataclass
class ProgramMetadata:
    """Structured program metadata"""
    program_name: str
    description: Optional[str]
    bounty_ranges: Optional[Dict[str, str]]  # {severity: amount, ...}
    asset_categories: List[str]
    auth_required: Optional[bool]
    auth_details: Optional[str]
    severity_levels: List[Dict[str, Any]]
    submission_requirements: List[str]
    prohibited_actions: List[str]
    platform_restrictions: Optional[str]
    payout_schedule: Optional[str]
    rules_of_engagement: Optional[str]
    
    def to_dict(self):
        return asdict(self)


class ProgramMetadataAnalyzer:
    """
    Analyze Bugcrowd program metadata
    Extract bounty info, requirements, and rules
    """
    
    def __init__(self, claude_client: ClaudeClient):
        self.claude = claude_client
    
    async def analyze_program_metadata(
        self,
        program_name: str,
        program_description: Optional[str],
        full_text: str
    ) -> ProgramMetadata:
        """
        Analyze program page for metadata
        
        Args:
            program_name: Program name
            program_description: Program description
            full_text: Full page text content
            
        Returns:
            Structured ProgramMetadata
        """
        
        metadata = ProgramMetadata(
            program_name=program_name,
            description=program_description,
            bounty_ranges={},
            asset_categories=[],
            auth_required=None,
            auth_details=None,
            severity_levels=[],
            submission_requirements=[],
            prohibited_actions=[],
            platform_restrictions=None,
            payout_schedule=None,
            rules_of_engagement=None
        )
        
        # Extract metadata from text
        try:
            # Use AI for intelligent analysis
            ai_metadata = await self._analyze_with_claude(program_name, full_text)
            
            # Merge AI results
            metadata.bounty_ranges = ai_metadata.get("bounty_ranges", {})
            metadata.asset_categories = ai_metadata.get("asset_categories", [])
            metadata.auth_required = ai_metadata.get("auth_required")
            metadata.auth_details = ai_metadata.get("auth_details")
            metadata.severity_levels = ai_metadata.get("severity_levels", [])
            metadata.submission_requirements = ai_metadata.get("submission_requirements", [])
            metadata.prohibited_actions = ai_metadata.get("prohibited_actions", [])
            metadata.payout_schedule = ai_metadata.get("payout_schedule")
            metadata.rules_of_engagement = ai_metadata.get("rules_of_engagement")
        
        except Exception as e:
            logger.error(f"Error analyzing metadata with Claude: {str(e)}")
            # Fall back to pattern matching
            self._extract_metadata_patterns(full_text, metadata)
        
        return metadata
    
    async def _analyze_with_claude(
        self,
        program_name: str,
        full_text: str
    ) -> Dict[str, Any]:
        """Use Claude to intelligently extract metadata"""
        
        prompt = f"""You are analyzing a bug bounty program engagement page.

Program name: {program_name}

Page content:
---
{full_text[:3000]}  # Truncate to avoid token limits
---

Extract metadata from the program page. Return ONLY valid JSON with this structure:
{{
  "bounty_ranges": {{
    "critical": "amount or range if mentioned",
    "high": "amount or range if mentioned",
    "medium": "amount or range if mentioned",
    "low": "amount or range if mentioned"
  }},
  "asset_categories": ["website", "api", "mobile", "cloud", "source_code", etc.],
  "auth_required": true/false/null,
  "auth_details": "specific auth details mentioned if any",
  "severity_levels": [
    {{
      "level": "critical",
      "bounty": "$amount if specified",
      "description": "brief description if provided"
    }}
  ],
  "submission_requirements": ["requirement 1", "requirement 2"],
  "prohibited_actions": ["action 1", "action 2"],
  "payout_schedule": "description of payout timeline",
  "rules_of_engagement": "key rules mentioned"
}}

Rules:
1. Extract ONLY information explicitly stated in the text
2. For bounty amounts, use exact values mentioned
3. For asset categories, identify from context clues
4. Return null for auth_required if not mentioned
5. Return empty arrays if nothing found for that category
6. Do NOT invent or assume information

Return only valid JSON, no additional text."""
        
        try:
            response = await self.claude.query_async(
                prompt,
                temperature=0.1,
                max_tokens=1500
            )
            
            # Parse JSON response
            json_match = re.search(r"\{[\s\S]*\}", response)
            if json_match:
                return json.loads(json_match.group())
        
        except Exception as e:
            logger.error(f"Claude analysis failed: {str(e)}")
        
        return {}
    
    def _extract_metadata_patterns(self, text: str, metadata: ProgramMetadata):
        """
        Fallback pattern-based metadata extraction
        """
        text_lower = text.lower()
        
        # Extract bounty amounts
        bounty_pattern = r"\$?([\d,]+(?:\.\d{2})?)\s*(?:to|[-–])\s*\$?([\d,]+(?:\.\d{2})?)"
        for severity in ["critical", "high", "medium", "low"]:
            if severity in text_lower:
                # Look for pattern near severity keyword
                idx = text_lower.index(severity)
                context = text[max(0, idx-100):idx+100]
                match = re.search(bounty_pattern, context)
                if match:
                    metadata.bounty_ranges[severity] = f"${match.group(1)} - ${match.group(2)}"
        
        # Extract auth requirements
        if any(phrase in text_lower for phrase in ["requires authentication", "auth required", "login needed"]):
            metadata.auth_required = True
        elif any(phrase in text_lower for phrase in ["no authentication", "unauthenticated", "public access"]):
            metadata.auth_required = False
        
        # Classify assets
        assets_keywords = {
            "website": ["website", "web app", "web application"],
            "api": ["api", "rest api", "graphql", "webhook"],
            "mobile": ["mobile", "ios", "android", "app"],
            "cloud": ["aws", "azure", "gcp", "cloud"],
            "source_code": ["source code", "github", "gitlab"]
        }
        
        for asset_type, keywords in assets_keywords.items():
            if any(keyword in text_lower for keyword in keywords):
                metadata.asset_categories.append(asset_type)
        
        # Extract severity levels
        for severity in ["critical", "high", "medium", "low", "info"]:
            if severity in text_lower:
                metadata.severity_levels.append({
                    "level": severity,
                    "mentioned": True
                })
    
    def classify_program_assets(self, metadata: ProgramMetadata) -> Dict[str, List[str]]:
        """
        Classify which asset types are in scope
        
        Args:
            metadata: Program metadata
            
        Returns:
            Dict mapping asset types to in-scope items
        """
        return {
            "asset_categories": metadata.asset_categories,
            "classified_at": "now"
        }
    
    def extract_program_rules(self, full_text: str) -> Dict[str, Any]:
        """
        Extract program-specific rules and restrictions
        
        Args:
            full_text: Full program page text
            
        Returns:
            Extracted rules
        """
        rules = {
            "prohibitions": [],
            "requirements": [],
            "guidelines": []
        }
        
        text_lower = full_text.lower()
        
        # Common rule patterns
        prohibition_keywords = [
            "do not", "don't", "prohibited", "not allowed",
            "forbidden", "illegal", "not permitted"
        ]
        
        requirement_keywords = [
            "required", "must", "should", "must include",
            "needs to", "please provide"
        ]
        
        lines = full_text.split("\n")
        
        for line in lines:
            line_lower = line.lower()
            
            for keyword in prohibition_keywords:
                if keyword in line_lower and len(line) > 20:
                    rules["prohibitions"].append(line.strip())
                    break
            
            for keyword in requirement_keywords:
                if keyword in line_lower and len(line) > 20:
                    rules["requirements"].append(line.strip())
                    break
        
        # Remove duplicates
        rules["prohibitions"] = list(set(rules["prohibitions"]))
        rules["requirements"] = list(set(rules["requirements"]))
        
        return rules
