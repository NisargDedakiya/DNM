import httpx
import asyncio
import logging
from backend.core.config import settings

logger = logging.getLogger(__name__)

class HackerOneAPIError(Exception):
    def __init__(self, message: str, status_code: int = 0):
        super().__init__(message)
        self.status_code = status_code

class HackerOneAuthError(HackerOneAPIError):
    pass

class HackerOneClient:
    BASE = 'https://api.hackerone.com/v1'

    def __init__(self):
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        if not self._client:
            self._client = httpx.AsyncClient(
                auth=(settings.hackerone_username, settings.hackerone_api_token),
                headers={'Accept': 'application/json',
                         'Content-Type': 'application/json'},
                timeout=30.0
            )
        return self._client

    async def _req(self, method: str, path: str, **kw) -> dict:
        client = await self._get_client()
        for attempt in range(3):
            r = await client.request(method, self.BASE + path, **kw)
            if r.status_code == 429:
                wait = int(r.headers.get('Retry-After', '10'))
                logger.warning(f'H1 rate limit — waiting {wait}s')
                await asyncio.sleep(wait)
                continue
            if r.status_code == 401:
                raise HackerOneAuthError('Invalid H1 credentials', 401)
            if r.status_code == 403:
                raise HackerOneAuthError('H1 Forbidden', 403)
            if r.status_code not in (200, 201):
                raise HackerOneAPIError(f'H1 error {r.status_code}: {r.text[:200]}', r.status_code)
            return r.json()
        raise HackerOneAPIError('H1 rate limit exceeded after retries', 429)

    async def get_programs(self) -> list[dict]:
        # Paginate through all programs — collect everything
        results = []
        cursor = None
        while True:
            params = {'page[size]': 100}
            if cursor:
                params['page[cursor]'] = cursor
            data = await self._req('GET', '/programs', params=params)
            for p in data.get('data', []):
                attrs = p.get('attributes', {})
                results.append({
                    'handle': attrs.get('handle', ''),
                    'name': attrs.get('name', ''),
                    'policy': attrs.get('policy', ''),
                    'offers_bounties': attrs.get('offers_bounties', False),
                    'state': attrs.get('state', 'public_mode'),
                    'is_private': attrs.get('state') not in ('public_mode', 'sandboxed'),
                    'structured_scope_enabled': attrs.get('structured_scope_enabled', False),
                })
            links = data.get('links', {})
            if not links.get('next'):
                break
            # Extract cursor from next URL
            import urllib.parse as up
            parsed = up.urlparse(links['next'])
            qs = up.parse_qs(parsed.query)
            cursor = qs.get('page[cursor]', [None])[0]
            if not cursor:
                break
        return results

    async def get_structured_scope(self, handle: str) -> dict:
        data = await self._req('GET', f'/programs/{handle}/structured_scopes')
        in_scope = []
        out_of_scope = []
        no_auto_scan = False
        for item in data.get('data', []):
            attrs = item.get('attributes', {})
            instruction = attrs.get('instruction', '') or ''
            if 'no automated' in instruction.lower() or 'no auto' in instruction.lower():
                no_auto_scan = True
            entry = {
                'asset_identifier': attrs.get('asset_identifier', ''),
                'asset_type': attrs.get('asset_type', 'url'),
                'eligible_for_bounty': attrs.get('eligible_for_bounty', False),
                'max_severity': attrs.get('max_severity', 'critical'),
                'instruction': instruction,
            }
            if attrs.get('eligible_for_submission', True):
                in_scope.append(entry)
            else:
                out_of_scope.append(entry)
        return {'in_scope': in_scope, 'out_of_scope': out_of_scope, 'no_auto_scan': no_auto_scan}

    async def get_program_policy(self, handle: str) -> dict:
        return await self._req('GET', f'/programs/{handle}')

    async def submit_report(self, handle: str, report: dict) -> dict:
        # Build the vulnerability_information from all report sections
        vuln_info = report.get('description', '')
        steps = report.get('steps_to_reproduce', [])
        if steps:
            vuln_info += '  ## Steps to Reproduce '
            for i, s in enumerate(steps, 1):
                vuln_info += f'{i}. {s} '
        vuln_info += f'  ## Impact {report.get("impact", "")}'
        vuln_info += f'  ## Remediation {report.get("remediation", "")}'
        body = {'data': {'type': 'report', 'attributes': {
            'team_handle': handle,
            'title': report['title'],
            'vulnerability_information': vuln_info,
            'severity_rating': report.get('severity', 'medium'),
            'impact': report.get('impact', ''),
        }}}
        if report.get('weakness_id'):
            body['data']['attributes']['weakness_id'] = report['weakness_id']
        result = await self._req('POST', '/reports', json=body)
        return {'submission_id': str(result['data']['id']), 'state': result['data']['attributes']['state']}

    async def get_my_reports(self) -> list[dict]:
        data = await self._req('GET', '/reports?filter[reporter]=me&page[size]=100')
        return [{'id': r['id'],
                 'title': r['attributes']['title'],
                 'state': r['attributes']['state'],
                 'bounty': r['attributes'].get('bounty_amount')}
                for r in data.get('data', [])]

    async def get_report_status(self, report_id: str) -> str:
        data = await self._req('GET', f'/reports/{report_id}')
        return data['data']['attributes']['state']

    async def get_hacktivity(self, handle: str, limit: int = 20) -> list[dict]:
        data = await self._req('GET',
            f'/hacktivity?filter[program]={handle}&filter[disclosed]=true&page[size]={limit}')
        return data.get('data', [])

    async def get_weakness_types(self) -> list[dict]:
        data = await self._req('GET', '/weakness_types')
        return [{'id': w['id'], 'name': w['attributes']['name']}
                for w in data.get('data', [])]

    async def close(self):
        if self._client:
            await self._client.aclose()

# Singleton
h1_client = HackerOneClient()
