from bs4 import BeautifulSoup
import httpx
import logging
from backend.ai.claude_client import claude

logger = logging.getLogger(__name__)

SCOPE_SYS = '''
Extract bug bounty scope from a Bugcrowd program page.
Handle tables, lists, paragraphs — any format.
Be conservative: if unclear, put in out_of_scope.
Return ONLY valid JSON:
{
  "program_name": str,
  "in_scope": [{"asset": str, "type": "web"|"mobile"|"api"|"other"}],
  "out_of_scope": [{"asset": str}],
  "no_automated_scan": bool,
  "bounty_range": {"p1": str, "p2": str, "p3": str, "p4": str},
  "special_rules": [str],
  "vdp_only": bool
}
'''

class BugcrowdError(Exception):
    pass

class BugcrowdScraper:

    HEADERS = {'User-Agent': 'Mozilla/5.0 (compatible; security-research/1.0)'}

    def _validate(self, url: str) -> str:
        if 'bugcrowd.com' not in url.lower():
            raise BugcrowdError('URL must be a bugcrowd.com URL')
        return url if url.startswith('http') else 'https://'+url

    def _extract_text(self, html: str) -> str:
        soup = BeautifulSoup(html, 'html.parser')
        for tag in soup(['script', 'style', 'nav', 'footer', 'header', 'aside']):
            tag.decompose()
        main = (soup.find('main') or
                soup.find('div', {'class': lambda c: c and 'content' in c.lower()}) or
                soup)
        lines = [l.strip() for l in main.get_text(' ').split(' ') if l.strip()]
        return ' '.join(lines[:400])

    async def fetch(self, url: str) -> dict:
        url = self._validate(url)
        async with httpx.AsyncClient(follow_redirects=True, timeout=15,
                                      headers=self.HEADERS) as client:
            try:
                r = await client.get(url)
            except httpx.TimeoutException:
                raise BugcrowdError('Request timed out')
            except httpx.RequestError as e:
                raise BugcrowdError(f'Request failed: {e}')
        if r.status_code == 404:
            raise BugcrowdError('Program not found — check the URL')
        if r.status_code != 200:
            raise BugcrowdError(f'HTTP {r.status_code}')

        # Try to find React props containing API endpoints
        soup = BeautifulSoup(r.text, 'html.parser')
        brief_root = soup.find(id='researcher-engagement-brief-root')
        
        json_data = None
        if brief_root:
            try:
                import json
                endpoints = json.loads(brief_root.get('data-api-endpoints', '{}'))
                changelog_path = endpoints.get('engagementBriefApi', {}).get('getBriefVersionDocument')
                if changelog_path:
                    changelog_url = f"https://bugcrowd.com{changelog_path}.json"
                    async with httpx.AsyncClient(follow_redirects=True, timeout=15, headers=self.HEADERS) as client:
                        r_json = await client.get(changelog_url)
                        if r_json.status_code == 200:
                            json_data = r_json.json()
            except Exception as e:
                logger.warning(f"Failed to fetch brief JSON from endpoints: {e}")

        if json_data:
            # Construct a rich text representation of the program from JSON
            brief_data = json_data.get('data', {})
            brief = brief_data.get('brief', {})
            program_name = brief.get('name', '')
            description = BeautifulSoup(brief.get('description', ''), 'html.parser').get_text(' ')
            
            lines = [
                f"Program Name: {program_name}",
                f"Description: {description}",
                "Scope Targets:"
            ]
            
            scope_groups = brief_data.get('scope', [])
            for group in scope_groups:
                in_scope = group.get('inScope', True)
                group_name = group.get('name', '')
                lines.append(f"Group: {group_name} (In-Scope: {in_scope})")
                for t in group.get('targets', []):
                    name = t.get('name', '')
                    category = t.get('category', '')
                    lines.append(f"  - Asset: {name} | Type: {category}")
                    
            text = '\n'.join(lines)
        else:
            text = self._extract_text(r.text)

        if len(text) < 50:
            raise BugcrowdError('Could not extract content — page may need login')
        scope = await claude.analyze_json(text[:8000], SCOPE_SYS)
        if not isinstance(scope, dict):
            raise BugcrowdError('Failed to parse scope')
        scope['source_url'] = url
        scope['platform'] = 'bugcrowd'
        return scope

bugcrowd_scraper = BugcrowdScraper()
