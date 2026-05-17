"""
HackerOne API client for bug bounty program integration.
Uses official HackerOne API v1.
"""
import base64
import logging
from typing import Any, Dict, List, Optional
import httpx

from backend.core.config import settings

logger = logging.getLogger(__name__)

class HackerOneClientError(Exception):
    pass

class HackerOneClient:
    """Async client for HackerOne API."""
    
    BASE_URL = "https://api.hackerone.com/v1"
    
    def __init__(self, username: Optional[str] = None, api_token: Optional[str] = None):
        self.username = username or settings.hackerone_username
        self.api_token = api_token or settings.hackerone_api_token
        
    def _get_headers(self) -> Dict[str, str]:
        if not self.username or not self.api_token:
            raise HackerOneClientError("HackerOne credentials not configured")
            
        auth_string = f"{self.username}:{self.api_token}"
        encoded_auth = base64.b64encode(auth_string.encode()).decode()
        
        return {
            "Authorization": f"Basic {encoded_auth}",
            "Accept": "application/json",
            "Content-Type": "application/json"
        }

    async def fetch_programs(self, page: int = 1, limit: int = 100) -> List[Dict[str, Any]]:
        """Fetch programs the authenticated user has access to."""
        headers = self._get_headers()
        url = f"{self.BASE_URL}/programs?page[number]={page}&page[size]={limit}"
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.get(url, headers=headers)
                response.raise_for_status()
                data = response.json()
                return data.get("data", [])
            except httpx.HTTPError as e:
                logger.error(f"HackerOne fetch_programs error: {str(e)}")
                raise HackerOneClientError(f"Failed to fetch programs: {str(e)}")

    async def fetch_program_scopes(self, handle: str, page: int = 1, limit: int = 100) -> List[Dict[str, Any]]:
        """Fetch structured scope for a specific program handle."""
        headers = self._get_headers()
        url = f"{self.BASE_URL}/programs/{handle}/structured_scopes?page[number]={page}&page[size]={limit}"
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.get(url, headers=headers)
                response.raise_for_status()
                data = response.json()
                return data.get("data", [])
            except httpx.HTTPError as e:
                logger.error(f"HackerOne fetch_program_scopes error for {handle}: {str(e)}")
                raise HackerOneClientError(f"Failed to fetch scopes for {handle}: {str(e)}")
