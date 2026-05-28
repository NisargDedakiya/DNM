"""
HackerOne API client.

Scope parsing is STRICT:
  - Only asset_types URL, WILDCARD, CIDR are harvested for scanning.
  - An entry is in-scope only when eligible_for_submission is True
    (falls back to eligible_for_bounty when the field is absent).
  - asset_identifier values are cleaned / normalised before being stored
    to prevent null or malformed entries from entering the scan pipeline.
"""
import httpx
import asyncio
import logging
from typing import Any

from backend.core.config import settings

logger = logging.getLogger(__name__)

# Asset types that have executable targets (domains / wildcards / IP ranges).
# Hardware, Android, iOS, etc. are intentionally excluded because they are
# not scannable domain targets and must not bleed into the URL pipeline.
_SCANNABLE_ASSET_TYPES: frozenset[str] = frozenset({"URL", "WILDCARD", "CIDR"})


class HackerOneAPIError(Exception):
    def __init__(self, message: str, status_code: int = 0):
        super().__init__(message)
        self.status_code = status_code


class HackerOneAuthError(HackerOneAPIError):
    pass


def _clean_asset_identifier(raw: str) -> str | None:
    """Normalise and validate an asset_identifier string.

    Returns the cleaned string, or ``None`` if the value is empty / unusable.
    """
    if not raw:
        return None
    cleaned = raw.strip().lower().rstrip("/")
    # Reject obviously malformed entries (whitespace-only, bare protocol, etc.)
    if not cleaned or cleaned in ("http://", "https://", "*", "**"):
        return None
    return cleaned


class HybridScopeList(list):
    """A list of raw API scope items that also exposes dict-like .get() access
    for the categorised in_scope / out_of_scope / no_auto_scan keys.

    This keeps backwards-compatibility with code that calls
    ``scope_data.get('in_scope')``.
    """

    def __init__(
        self,
        items: list,
        in_scope: list[dict],
        out_of_scope: list[dict],
        no_auto_scan: bool,
    ) -> None:
        super().__init__(items)
        self._dict: dict[str, Any] = {
            "in_scope": in_scope,
            "out_of_scope": out_of_scope,
            "no_auto_scan": no_auto_scan,
        }

    def get(self, key: str, default=None):
        return self._dict.get(key, default)

    def __getitem__(self, item):
        if isinstance(item, str):
            return self._dict[item]
        return super().__getitem__(item)


class HackerOneClient:
    BASE = "https://api.hackerone.com/v1"
    RETRIES = 3

    def __init__(
        self,
        username: str | None = None,
        api_token: str | None = None,
    ) -> None:
        self.username = username or settings.hackerone_username
        self.api_token = api_token or settings.hackerone_api_token
        self._client: httpx.AsyncClient | None = None

    async def _client_instance(self) -> httpx.AsyncClient:
        if not self._client:
            self._client = httpx.AsyncClient(
                auth=(self.username, self.api_token),
                headers={
                    "Accept": "application/json",
                    "Content-Type": "application/json",
                },
                timeout=30.0,
            )
        return self._client

    async def _request(self, method: str, path: str, **kwargs) -> dict:
        client = await self._client_instance()
        for attempt in range(self.RETRIES):
            try:
                response = await client.request(method, self.BASE + path, **kwargs)
                if response.status_code == 429:
                    wait = int(response.headers.get("Retry-After", "10"))
                    logger.warning(f"H1 rate limit hit — waiting {wait}s")
                    await asyncio.sleep(wait)
                    continue
                if response.status_code == 401:
                    raise HackerOneAPIError(
                        "Invalid HackerOne credentials — check API token", 401
                    )
                if response.status_code == 403:
                    raise HackerOneAPIError(
                        "Forbidden — check account permissions", 403
                    )
                if response.status_code not in (200, 201, 204):
                    raise HackerOneAPIError(
                        f"H1 API returned {response.status_code}: {response.text[:300]}",
                        response.status_code,
                    )
                if response.status_code == 204:
                    return {}
                return response.json()
            except httpx.RequestError as e:
                if attempt == self.RETRIES - 1:
                    raise HackerOneAPIError(f"Network error: {e}")
                await asyncio.sleep(2**attempt)
        raise HackerOneAPIError("Max retries exceeded")

    async def authenticate(self) -> dict:
        try:
            data = await self._request("GET", "/programs", params={"page[size]": 1})
            programs_data = data.get("data", [])
            return {"program_count_hint": len(programs_data)}
        except HackerOneAPIError as e:
            if e.status_code in (401, 403):
                raise HackerOneAuthError(str(e), e.status_code)
            raise

    async def get_programs(self) -> list[dict]:
        """Paginate through ALL accessible HackerOne programs."""
        results: list[dict] = []
        cursor: str | None = None

        while True:
            params: dict = {"page[size]": 100}
            if cursor:
                params["page[cursor]"] = cursor

            data = await self._request("GET", "/programs", params=params)

            for p in data.get("data", []):
                attrs = p.get("attributes", {})
                results.append(
                    {
                        "id": p.get("id", ""),
                        "handle": attrs.get("handle", ""),
                        "name": attrs.get("name", ""),
                        "state": attrs.get("state", "public_mode"),
                        "is_active": True,
                        "is_private": attrs.get("state")
                        not in ("public_mode", "sandboxed"),
                        "offers_bounties": attrs.get("offers_bounties", False),
                        "structured_scope_enabled": attrs.get(
                            "structured_scope_enabled", False
                        ),
                        "policy": attrs.get("policy", ""),
                        # Compatibility shim for HackerOneSyncService and others
                        "attributes": {
                            "handle": attrs.get("handle", ""),
                            "name": attrs.get("name", ""),
                            "state": attrs.get("state", "public_mode"),
                            "offers_bounties": attrs.get("offers_bounties", False),
                            "submission_state": (
                                "open"
                                if attrs.get("state") == "public_mode"
                                else "closed"
                            ),
                        },
                    }
                )

            next_link = data.get("links", {}).get("next")
            if not next_link:
                break

            import urllib.parse as urlparse

            parsed = urlparse.urlparse(next_link)
            qs = urlparse.parse_qs(parsed.query)
            cursor = qs.get("page[cursor]", [None])[0]
            if not cursor:
                break

        logger.info(f"Fetched {len(results)} programs from HackerOne")
        return results

    async def get_structured_scope(self, handle: str) -> HybridScopeList:
        """Fetch and strictly categorise the structured scopes for *handle*.

        Filtering rules (applied to every item in the API response):
        1. ``asset_type`` MUST be one of ``URL``, ``WILDCARD``, or ``CIDR``.
           Any other type (Android, iOS, Hardware, Other, …) is silently
           excluded — these are not domain/IP targets and must never reach the
           scan pipeline.
        2. The item is considered **in-scope** if EITHER:
           - ``eligible_for_submission`` is ``True``  (primary field), OR
           - ``eligible_for_submission`` is absent AND ``eligible_for_bounty``
             is ``True``  (legacy fallback).
        3. ``asset_identifier`` is normalised through ``_clean_asset_identifier``.
           Items with a null/empty identifier after cleaning are dropped entirely.

        Returns a :class:`HybridScopeList` whose ``.get('in_scope')`` gives the
        curated list ready for scope-validation and DB persistence.
        """
        data = await self._request(
            "GET", f"/programs/{handle}/structured_scopes"
        )

        in_scope: list[dict] = []
        out_of_scope: list[dict] = []
        no_auto_scan: bool = False
        raw_items: list = data.get("data", [])

        for item in raw_items:
            attrs = item.get("attributes", {})

            # ── 1. Asset-type gate ───────────────────────────────────────────
            raw_asset_type: str = (attrs.get("asset_type") or "").upper().strip()
            if raw_asset_type not in _SCANNABLE_ASSET_TYPES:
                logger.debug(
                    "Skipping H1 scope item for %s — non-scannable asset_type=%r",
                    handle,
                    raw_asset_type,
                )
                continue

            # ── 2. Clean / validate asset_identifier ─────────────────────────
            raw_identifier: str = attrs.get("asset_identifier") or ""
            identifier = _clean_asset_identifier(raw_identifier)
            if identifier is None:
                logger.warning(
                    "Skipping H1 scope item for %s — malformed identifier=%r",
                    handle,
                    raw_identifier,
                )
                continue

            # ── 3. No-auto-scan flag ─────────────────────────────────────────
            instruction: str = (attrs.get("instruction") or "").lower()
            if "no automated" in instruction or "no auto" in instruction:
                no_auto_scan = True

            # ── 4. Eligibility check ─────────────────────────────────────────
            # eligible_for_submission is the canonical field; fall back to
            # eligible_for_bounty only when the key is literally absent.
            if "eligible_for_submission" in attrs:
                eligible = bool(attrs["eligible_for_submission"])
            else:
                eligible = bool(attrs.get("eligible_for_bounty", False))

            entry: dict = {
                "asset_identifier": identifier,
                "asset_type": raw_asset_type,
                "eligible_for_bounty": bool(attrs.get("eligible_for_bounty", False)),
                "eligible_for_submission": eligible,
                "max_severity": attrs.get("max_severity", "critical"),
                "instruction": instruction,
            }

            if eligible:
                in_scope.append(entry)
            else:
                out_of_scope.append(entry)

        logger.info(
            "H1 structured scope for %s: %d in-scope, %d out-of-scope "
            "(asset_types: URL/WILDCARD/CIDR only), no_auto_scan=%s",
            handle,
            len(in_scope),
            len(out_of_scope),
            no_auto_scan,
        )

        return HybridScopeList(raw_items, in_scope, out_of_scope, no_auto_scan)

    async def get_program_policy(self, handle: str) -> dict:
        return await self._request("GET", f"/programs/{handle}")

    async def submit_report(self, handle: str, report: dict) -> dict:
        vuln_info = report.get("description", "")
        steps = report.get("steps_to_reproduce", [])
        if steps:
            vuln_info += "  ## Steps to Reproduce "
            for i, step in enumerate(steps, 1):
                vuln_info += f"{i}. {step} "
        vuln_info += f"  ## Impact {report.get('impact', '')}"
        vuln_info += f"  ## Remediation {report.get('remediation', '')}"

        body = {
            "data": {
                "type": "report",
                "attributes": {
                    "team_handle": handle,
                    "title": report["title"],
                    "vulnerability_information": vuln_info,
                    "severity_rating": report.get("severity", "medium"),
                    "impact": report.get("impact", ""),
                },
            }
        }
        if report.get("weakness_id"):
            body["data"]["attributes"]["weakness_id"] = report["weakness_id"]

        result = await self._request("POST", "/reports", json=body)
        return {
            "submission_id": str(result["data"]["id"]),
            "state": result["data"]["attributes"]["state"],
        }

    async def get_my_reports(self) -> list[dict]:
        data = await self._request(
            "GET", "/reports?filter[reporter]=me&page[size]=100"
        )
        raw_reports = data.get("data", [])
        return [
            {
                "id": r["id"],
                "title": r["attributes"]["title"],
                "state": r["attributes"]["state"],
                "bounty": r["attributes"].get("bounty_amount"),
                "attributes": r["attributes"],
            }
            for r in raw_reports
        ]

    async def get_report_status(self, report_id: str) -> str:
        data = await self._request("GET", f"/reports/{report_id}")
        return data["data"]["attributes"]["state"]

    async def get_hacktivity(self, handle: str, limit: int = 20) -> list[dict]:
        data = await self._request(
            "GET",
            f"/hacktivity?filter[program]={handle}&filter[disclosed]=true&page[size]={limit}",
        )
        return data.get("data", [])

    async def close(self) -> None:
        if self._client:
            await self._client.aclose()


# Singleton — import this everywhere that needs H1 access
h1_client = HackerOneClient()
