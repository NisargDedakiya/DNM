from bs4 import BeautifulSoup
import httpx
import logging
from backend.ai.claude_client import claude, ClaudeAPIError

logger = logging.getLogger(__name__)

SCOPE_SYSTEM = '''
Extract bug bounty scope from a Bugcrowd program page.
Handle any format: HTML tables, bullet lists, plain text paragraphs.
Be CONSERVATIVE: if scope of an asset is unclear, put it in out_of_scope.
Return ONLY valid JSON:
{
  "program_name": str,
  "in_scope": [{"asset": str, "type": "web"|"mobile"|"api"|"other", "notes": str}],
  "out_of_scope": [{"asset": str, "reason": str}],
  "no_automated_scan": bool,
  "bounty_range": {"p1": str, "p2": str, "p3": str, "p4": str},
  "special_rules": [str],
  "vdp_only": bool
}
If no clear in_scope found, return empty in_scope list.
'''


class BugcrowdScrapeError(Exception):
    pass


class BugcrowdScraper:

    HEADERS = {
        'User-Agent': 'Mozilla/5.0 (compatible; security-research-bot/1.0)',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9',
        'Accept-Language': 'en-US,en;q=0.9',
    }

    def _validate_url(self, url: str) -> str:
        if 'bugcrowd.com' not in url.lower():
            raise BugcrowdScrapeError('URL must be a bugcrowd.com URL')
        if not url.startswith('http'):
            url = 'https://' + url
        return url

    def _extract_text(self, html: str) -> str:
        soup = BeautifulSoup(html, 'html.parser')
        # Remove noise elements
        for tag in soup(['script', 'style', 'nav', 'footer',
                         'header', 'aside', 'noscript', 'meta', 'link']):
            tag.decompose()
        # Try to find main content area first
        main = (
            soup.find('main') or
            soup.find('div', {'class': lambda c: c and 'content' in c.lower()}) or
            soup.find('div', {'id': 'main'}) or
            soup.body or
            soup
        )
        # Extract clean lines
        raw_text = main.get_text(separator=' ', strip=True)
        lines = [line.strip() for line in raw_text.split(' ') if line.strip()]
        # Cap at 400 lines to stay within Claude context window
        return ' '.join(lines[:400])

    def _extract_from_brief_json(self, html: str) -> str | None:
        """
        Try to pull richer data from the embedded React props / API endpoint.
        Returns a structured text block or None if unavailable.
        """
        try:
            import json as _json
            soup = BeautifulSoup(html, 'html.parser')
            brief_root = soup.find(id='researcher-engagement-brief-root')
            if not brief_root:
                return None
            endpoints = _json.loads(brief_root.get('data-api-endpoints', '{}'))
            return endpoints.get('engagementBriefApi', {}).get('getBriefVersionDocument')
        except Exception:
            return None

    async def fetch_and_parse(self, engagement_url: str) -> dict:
        url = self._validate_url(engagement_url)
        async with httpx.AsyncClient(
            follow_redirects=True,
            timeout=20.0,
            headers=self.HEADERS,
        ) as client:
            try:
                response = await client.get(url)
            except httpx.TimeoutException:
                raise BugcrowdScrapeError('Request timed out — the page took too long to respond')
            except httpx.RequestError as e:
                raise BugcrowdScrapeError(f'Could not fetch the URL: {e}')

            if response.status_code == 404:
                raise BugcrowdScrapeError('Program not found — check the Bugcrowd URL')
            if response.status_code == 403:
                raise BugcrowdScrapeError('Access denied — this program may require login')
            if response.status_code != 200:
                raise BugcrowdScrapeError(f'HTTP {response.status_code} from Bugcrowd')

            # Try to fetch structured brief JSON via the embedded API endpoint path
            changelog_path = self._extract_from_brief_json(response.text)
            text: str | None = None
            if changelog_path:
                try:
                    changelog_url = f'https://bugcrowd.com{changelog_path}.json'
                    r_json = await client.get(changelog_url)
                    if r_json.status_code == 200:
                        data = r_json.json().get('data', {})
                        brief = data.get('brief', {})
                        program_name = brief.get('name', '')
                        description = BeautifulSoup(
                            brief.get('description', ''), 'html.parser'
                        ).get_text(' ')
                        lines = [
                            f'Program Name: {program_name}',
                            f'Description: {description}',
                            'Scope Targets:',
                        ]
                        for group in data.get('scope', []):
                            in_s = group.get('inScope', True)
                            lines.append(f'Group: {group.get("name", "")} (In-Scope: {in_s})')
                            for t in group.get('targets', []):
                                lines.append(
                                    f'  - Asset: {t.get("name", "")} | Type: {t.get("category", "")}'
                                )
                        text = '\n'.join(lines)
                except Exception as e:
                    logger.warning(f'Failed to fetch brief JSON: {e}')

        if not text:
            text = self._extract_text(response.text)

        if len(text) < 100:
            raise BugcrowdScrapeError(
                'Could not extract content — page may be JavaScript-only or require login'
            )

        try:
            scope = await claude.analyze_json(text[:8000], SCOPE_SYSTEM)
        except ClaudeAPIError as e:
            raise BugcrowdScrapeError(f'AI parsing failed: {e}')

        if not isinstance(scope, dict):
            raise BugcrowdScrapeError('AI returned unexpected data format')

        scope['source_url'] = engagement_url
        scope['platform'] = 'bugcrowd'
        logger.info(
            f'Scraped Bugcrowd program: {scope.get("program_name")} '
            f'— {len(scope.get("in_scope", []))} in-scope assets'
        )
        return scope


# Singleton — import this everywhere that needs Bugcrowd scraping
bugcrowd_scraper = BugcrowdScraper()

# Backward-compat alias so existing imports of BugcrowdError still resolve
BugcrowdError = BugcrowdScrapeError
