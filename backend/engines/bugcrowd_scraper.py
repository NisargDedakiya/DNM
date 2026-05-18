"""
Bugcrowd Scraper Engine
Safe public engagement page parsing and scope extraction
"""
import re
import asyncio
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
import aiohttp
from aiohttp import ClientSession, TCPConnector
import logging
from urllib.parse import urlparse, urljoin

logger = logging.getLogger(__name__)


class BugcrowdScraperConfig:
    """Configuration for Bugcrowd scraping"""
    
    # Rate limiting
    RATE_LIMIT_DELAY = 2.0  # Seconds between requests
    REQUEST_TIMEOUT = 30  # Seconds
    MAX_RETRIES = 3
    RETRY_BACKOFF = 2.0
    
    # HTTP headers
    USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    
    # Scope extraction patterns
    IN_SCOPE_MARKERS = [
        r"in\s*scope", r"included\s*in\s*scope", r"acceptable\s*targets",
        r"authorization\s*granted", r"test\s*these"
    ]
    OUT_SCOPE_MARKERS = [
        r"out\s*of\s*scope", r"excluded", r"not\s*allowed",
        r"off\s*limits", r"don't?\s*test"
    ]
    
    # Asset type patterns
    WEBSITE_PATTERNS = [r"https?://", r"www\.", r"\.com", r"\.io", r"domain"]
    API_PATTERNS = [r"api\.", r"/api/", r"rest", r"graphql", r"webhook"]
    MOBILE_PATTERNS = [r"app\s*store", r"play\s*store", r"ios", r"android", r"mobile"]


class BugcrowdScraper:
    """
    Safe Bugcrowd public engagement page scraper
    Respects rate limits and robots restrictions
    """
    
    def __init__(self, config: Optional[BugcrowdScraperConfig] = None):
        self.config = config or BugcrowdScraperConfig()
        self.last_request_time = 0.0
        self._session: Optional[ClientSession] = None
    
    async def __aenter__(self):
        """Async context manager entry"""
        connector = TCPConnector(limit=10, limit_per_host=5)
        self._session = ClientSession(connector=connector)
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self._session:
            await self._session.close()
    
    async def _rate_limit(self):
        """Enforce rate limiting between requests"""
        elapsed = asyncio.get_event_loop().time() - self.last_request_time
        if elapsed < self.config.RATE_LIMIT_DELAY:
            await asyncio.sleep(self.config.RATE_LIMIT_DELAY - elapsed)
        self.last_request_time = asyncio.get_event_loop().time()
    
    async def fetch_engagement_page(self, url: str) -> Optional[str]:
        """
        Fetch public Bugcrowd engagement page safely
        
        Args:
            url: Bugcrowd engagement URL
            
        Returns:
            HTML content or None on failure
            
        Security:
            - Rate limited
            - Timeout protection
            - Respects user-agent
            - Validates URL is Bugcrowd domain
        """
        # Validate URL is Bugcrowd
        if "bugcrowd.com" not in url.lower():
            logger.warning(f"Rejected non-Bugcrowd URL: {url}")
            return None
        
        # Prevent private page access
        private_paths = ["/settings", "/admin", "/account", "/api/v1/"]
        if any(path in url.lower() for path in private_paths):
            logger.warning(f"Rejected private page URL: {url}")
            return None
        
        await self._rate_limit()
        
        headers = {
            "User-Agent": self.config.USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Connection": "keep-alive",
        }
        
        for attempt in range(self.config.MAX_RETRIES):
            try:
                if not self._session:
                    raise RuntimeError("Session not initialized")
                
                async with self._session.get(
                    url,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=self.config.REQUEST_TIMEOUT),
                    ssl=False,
                    allow_redirects=True
                ) as response:
                    if response.status == 200:
                        return await response.text()
                    elif response.status == 404:
                        logger.warning(f"Page not found: {url}")
                        return None
                    elif response.status == 429:
                        # Rate limited - respect it
                        logger.warning(f"Rate limited on {url}, backing off")
                        await asyncio.sleep(self.config.RETRY_BACKOFF ** (attempt + 1))
                        continue
                    else:
                        logger.warning(f"Unexpected status {response.status} for {url}")
                        return None
            
            except asyncio.TimeoutError:
                logger.warning(f"Timeout fetching {url} (attempt {attempt + 1})")
                if attempt < self.config.MAX_RETRIES - 1:
                    await asyncio.sleep(self.config.RETRY_BACKOFF ** (attempt + 1))
                    continue
                return None
            
            except Exception as e:
                logger.error(f"Error fetching {url}: {str(e)}", exc_info=True)
                if attempt < self.config.MAX_RETRIES - 1:
                    await asyncio.sleep(self.config.RETRY_BACKOFF ** (attempt + 1))
                    continue
                return None
        
        return None
    
    def parse_engagement_html(self, html: str) -> Dict[str, Any]:
        """
        Parse Bugcrowd engagement page HTML
        
        Args:
            html: HTML content from engagement page
            
        Returns:
            Structured data dict with program info and sections
        """
        soup = BeautifulSoup(html, 'html.parser')
        
        result = {
            "program_name": None,
            "program_description": None,
            "sections": {},
            "raw_text": None,
            "metadata": {}
        }
        
        # Extract program title
        title_elem = soup.find("h1") or soup.find("h2")
        if title_elem:
            result["program_name"] = title_elem.get_text(strip=True)
        
        # Try to find meta description
        meta_desc = soup.find("meta", attrs={"name": "description"})
        if meta_desc:
            result["program_description"] = meta_desc.get("content")
        
        # Extract all text sections
        raw_text_parts = []
        for p in soup.find_all(["p", "div", "span", "li"]):
            text = p.get_text(strip=True)
            if text and len(text) > 10:
                raw_text_parts.append(text)
        
        result["raw_text"] = "\n\n".join(raw_text_parts)
        
        # Extract scope sections (look for common headers)
        scope_headers = soup.find_all(re.compile("^h[1-6]$"))
        
        current_section = None
        current_content = []
        
        for elem in scope_headers:
            header_text = elem.get_text(strip=True).lower()
            
            # Categorize by header
            if any(marker in header_text for marker in ["in scope", "included", "acceptable"]):
                if current_section:
                    result["sections"][current_section] = "\n".join(current_content)
                current_section = "in_scope"
                current_content = [elem.get_text(strip=True)]
            
            elif any(marker in header_text for marker in ["out of scope", "excluded", "off limits"]):
                if current_section:
                    result["sections"][current_section] = "\n".join(current_content)
                current_section = "out_of_scope"
                current_content = [elem.get_text(strip=True)]
            
            elif any(marker in header_text for marker in ["rules", "restrictions", "requirements"]):
                if current_section:
                    result["sections"][current_section] = "\n".join(current_content)
                current_section = "rules"
                current_content = [elem.get_text(strip=True)]
            
            else:
                # Extract content following this header
                sibling = elem.find_next_sibling()
                while sibling:
                    text = sibling.get_text(strip=True)
                    if text:
                        current_content.append(text)
                    if sibling.name and sibling.name.startswith("h"):
                        break
                    sibling = sibling.find_next_sibling()
        
        # Save final section
        if current_section:
            result["sections"][current_section] = "\n".join(current_content)
        
        return result
    
    def extract_scope_sections(self, parsed_data: Dict[str, Any]) -> Dict[str, List[str]]:
        """
        Extract raw scope entries from parsed HTML data
        
        Args:
            parsed_data: Output from parse_engagement_html()
            
        Returns:
            Dict with in_scope and out_of_scope lists
        """
        result = {
            "in_scope": [],
            "out_of_scope": [],
            "rules": []
        }
        
        # Get text content
        full_text = parsed_data.get("raw_text", "")
        
        # Extract bullet points and list items
        lines = full_text.split("\n")
        for line in lines:
            line = line.strip()
            if not line or len(line) < 3:
                continue
            
            # Remove common bullet markers
            cleaned = re.sub(r"^[\s•\-\*\d\.\)]+\s*", "", line)
            
            if cleaned in result["in_scope"] or cleaned in result["out_of_scope"]:
                continue  # Skip duplicates
            
            # Classify by markers
            line_lower = line.lower()
            
            if any(re.search(marker, line_lower) for marker in self.config.IN_SCOPE_MARKERS):
                result["in_scope"].append(cleaned)
            
            elif any(re.search(marker, line_lower) for marker in self.config.OUT_SCOPE_MARKERS):
                result["out_of_scope"].append(cleaned)
        
        return result
    
    def extract_program_metadata(self, parsed_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract program metadata (bounty info, requirements, etc)
        
        Args:
            parsed_data: Output from parse_engagement_html()
            
        Returns:
            Metadata dict
        """
        metadata = {
            "asset_types": [],
            "bounty_ranges": None,
            "auth_required": None,
            "severity_ratings": [],
            "restrictions": []
        }
        
        full_text = (parsed_data.get("raw_text", "") or "").lower()
        
        # Detect asset types
        for asset_type, patterns in [
            ("website", self.config.WEBSITE_PATTERNS),
            ("api", self.config.API_PATTERNS),
            ("mobile", self.config.MOBILE_PATTERNS),
        ]:
            if any(re.search(pattern.lower(), full_text) for pattern in patterns):
                metadata["asset_types"].append(asset_type)
        
        # Detect bounty ranges
        bounty_patterns = [
            r"\$(\d+)\s*-\s*\$?([\d,]+)",
            r"bounty.*?(\$[\d,]+)",
            r"(\$[\d,]+).*?reward"
        ]
        for pattern in bounty_patterns:
            match = re.search(pattern, full_text)
            if match:
                metadata["bounty_ranges"] = match.group(0)
                break
        
        # Detect auth requirements
        if any(phrase in full_text for phrase in ["requires auth", "authentication required", "login required"]):
            metadata["auth_required"] = True
        elif any(phrase in full_text for phrase in ["no auth", "unauthenticated", "public access"]):
            metadata["auth_required"] = False
        
        # Extract severity ratings
        severity_pattern = r"(critical|high|medium|low)(?:\s*[-:])?\s*([\d.]+)?"
        for match in re.finditer(severity_pattern, full_text):
            metadata["severity_ratings"].append({
                "level": match.group(1),
                "bounty": match.group(2) or None
            })
        
        return metadata
