"""
Bugcrowd API client for bug bounty program integration.
Uses official Bugcrowd API.
"""
import logging
from typing import Any, Dict, List, Optional
import httpx

logger = logging.getLogger(__name__)

class BugcrowdClientError(Exception):
    pass

class BugcrowdClient:
    """Async client for Bugcrowd API."""
    
    BASE_URL = "https://api.bugcrowd.com"
    
    def __init__(self, api_token: Optional[str] = None):
        self.api_token = api_token
        
    def _get_headers(self) -> Dict[str, str]:
        if not self.api_token:
            raise BugcrowdClientError("Bugcrowd API token not configured")
            
        return {
            "Authorization": f"Token {self.api_token}",
            "Accept": "application/vnd.bugcrowd+json",
            "Content-Type": "application/json"
        }

    async def fetch_programs(self, page: int = 1, limit: int = 100) -> List[Dict[str, Any]]:
        """Fetch programs."""
        headers = self._get_headers()
        url = f"{self.BASE_URL}/programs" # Note: Adjust endpoint based on actual Bugcrowd API docs
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.get(url, headers=headers, params={"page": page, "per_page": limit})
                response.raise_for_status()
                data = response.json()
                return data.get("programs", []) # Adapt based on actual response structure
            except httpx.HTTPError as e:
                logger.error(f"Bugcrowd fetch_programs error: {str(e)}")
                raise BugcrowdClientError(f"Failed to fetch programs: {str(e)}")

    async def fetch_scopes(self, program_id: str) -> List[Dict[str, Any]]:
        """Fetch scopes for a program."""
        headers = self._get_headers()
        url = f"{self.BASE_URL}/programs/{program_id}/target_groups"
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.get(url, headers=headers)
                response.raise_for_status()
                data = response.json()
                return data.get("target_groups", []) # Adapt based on actual response structure
            except httpx.HTTPError as e:
                logger.error(f"Bugcrowd fetch_scopes error for {program_id}: {str(e)}")
                raise BugcrowdClientError(f"Failed to fetch scopes for {program_id}: {str(e)}")
