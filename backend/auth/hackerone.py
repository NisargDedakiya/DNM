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

class HybridScopeList(list):
    def __init__(self, items, in_scope, out_of_scope, no_auto_scan):
        super().__init__(items)
        self._dict = {
            'in_scope': in_scope,
            'out_of_scope': out_of_scope,
            'no_auto_scan': no_auto_scan
        }
    def get(self, key, default=None):
        return self._dict.get(key, default)
    def __getitem__(self, item):
        if isinstance(item, str):
            return self._dict[item]
        return super().__getitem__(item)

class HackerOneClient:
    BASE = 'https://api.hackerone.com/v1'
    RETRIES = 3

    def __init__(self, username: str | None = None, api_token: str | None = None):
        self.username = username or settings.hackerone_username
        self.api_token = api_token or settings.hackerone_api_token
        self._client: httpx.AsyncClient | None = None

    async def _client_instance(self) -> httpx.AsyncClient:
        if not self._client:
            self._client = httpx.AsyncClient(
                auth=(self.username, self.api_token),
                headers={'Accept': 'application/json', 'Content-Type': 'application/json'},
                timeout=30.0
            )
        return self._client

    async def _request(self, method: str, path: str, **kwargs) -> dict:
        client = await self._client_instance()
        for attempt in range(self.RETRIES):
            try:
                response = await client.request(method, self.BASE + path, **kwargs)
                if response.status_code == 429:
                    wait = int(response.headers.get('Retry-After', '10'))
                    logger.warning(f'H1 rate limit hit — waiting {wait}s')
                    await asyncio.sleep(wait)
                    continue
                if response.status_code == 401:
                    raise HackerOneAPIError('Invalid HackerOne credentials — check API token', 401)
                if response.status_code == 403:
                    raise HackerOneAPIError('Forbidden — check account permissions', 403)
                if response.status_code not in (200, 201, 204):
                    raise HackerOneAPIError(
                        f'H1 API returned {response.status_code}: {response.text[:300]}',
                        response.status_code
                    )
                if response.status_code == 204:
                    return {}
                return response.json()
            except httpx.RequestError as e:
                if attempt == self.RETRIES - 1:
                    raise HackerOneAPIError(f'Network error: {e}')
                await asyncio.sleep(2 ** attempt)
        raise HackerOneAPIError('Max retries exceeded')

    async def authenticate(self) -> dict:
        try:
            data = await self._request('GET', '/programs', params={'page[size]': 1})
            programs_data = data.get('data', [])
            return {"program_count_hint": len(programs_data)}
        except HackerOneAPIError as e:
            if e.status_code in (401, 403):
                raise HackerOneAuthError(str(e), e.status_code)
            raise

    async def get_programs(self) -> list[dict]:
        # Paginate through ALL programs
        results = []
        cursor = None
        while True:
            params: dict = {'page[size]': 100}
            if cursor:
                params['page[cursor]'] = cursor
            data = await self._request('GET', '/programs', params=params)
            for p in data.get('data', []):
                attrs = p.get('attributes', {})
                results.append({
                    'id': p.get('id', ''),
                    'handle': attrs.get('handle', ''),
                    'name': attrs.get('name', ''),
                    'state': attrs.get('state', 'public_mode'),
                    'is_active': True,
                    'is_private': attrs.get('state') not in ('public_mode', 'sandboxed'),
                    'offers_bounties': attrs.get('offers_bounties', False),
                    'structured_scope_enabled': attrs.get('structured_scope_enabled', False),
                    'policy': attrs.get('policy', ''),
                    # compatibility for HackerOneSyncService and others
                    'attributes': {
                        'handle': attrs.get('handle', ''),
                        'name': attrs.get('name', ''),
                        'state': attrs.get('state', 'public_mode'),
                        'offers_bounties': attrs.get('offers_bounties', False),
                        'submission_state': 'open' if attrs.get('state') == 'public_mode' else 'closed',
                    }
                })
            next_link = data.get('links', {}).get('next')
            if not next_link:
                break
            import urllib.parse as urlparse
            parsed = urlparse.urlparse(next_link)
            qs = urlparse.parse_qs(parsed.query)
            cursor = qs.get('page[cursor]', [None])[0]
            if not cursor:
                break
        logger.info(f'Fetched {len(results)} programs from HackerOne')
        return results

    async def get_structured_scope(self, handle: str) -> HybridScopeList:
        data = await self._request('GET', f'/programs/{handle}/structured_scopes')
        in_scope, out_of_scope, no_auto_scan = [], [], False
        raw_items = data.get('data', [])
        for item in raw_items:
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
        
        return HybridScopeList(raw_items, in_scope, out_of_scope, no_auto_scan)

    async def get_program_policy(self, handle: str) -> dict:
        return await self._request('GET', f'/programs/{handle}')

    async def submit_report(self, handle: str, report: dict) -> dict:
        # Build vulnerability_information from all report sections
        vuln_info = report.get('description', '')
        steps = report.get('steps_to_reproduce', [])
        if steps:
            vuln_info += '  ## Steps to Reproduce '
            for i, step in enumerate(steps, 1):
                vuln_info += f'{i}. {step} '
        vuln_info += f'  ## Impact {report.get("impact", "")}'
        vuln_info += f'  ## Remediation {report.get("remediation", "")}'
        body = {
            'data': {
                'type': 'report',
                'attributes': {
                    'team_handle': handle,
                    'title': report['title'],
                    'vulnerability_information': vuln_info,
                    'severity_rating': report.get('severity', 'medium'),
                    'impact': report.get('impact', ''),
                }
            }
        }
        if report.get('weakness_id'):
            body['data']['attributes']['weakness_id'] = report['weakness_id']
        result = await self._request('POST', '/reports', json=body)
        return {
            'submission_id': str(result['data']['id']),
            'state': result['data']['attributes']['state'],
        }

    async def get_my_reports(self) -> list[dict]:
        data = await self._request('GET', '/reports?filter[reporter]=me&page[size]=100')
        raw_reports = data.get('data', [])
        return [
            {
                'id': r['id'],
                'title': r['attributes']['title'],
                'state': r['attributes']['state'],
                'bounty': r['attributes'].get('bounty_amount'),
                'attributes': r['attributes']
            }
            for r in raw_reports
        ]

    async def get_report_status(self, report_id: str) -> str:
        data = await self._request('GET', f'/reports/{report_id}')
        return data['data']['attributes']['state']

    async def get_hacktivity(self, handle: str, limit: int = 20) -> list[dict]:
        data = await self._request(
            'GET',
            f'/hacktivity?filter[program]={handle}&filter[disclosed]=true&page[size]={limit}'
        )
        return data.get('data', [])

    async def close(self):
        if self._client:
            await self._client.aclose()

# Singleton — import this everywhere that needs H1 access
h1_client = HackerOneClient()
