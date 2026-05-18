"""
Official HackerOne API client wrapper.

Security posture:
- uses only official API endpoints
- accepts user-provided credentials (not persisted by default)
- async-safe with timeout, retries, pagination
- structured output parsing
"""
from __future__ import annotations

import asyncio
import base64
import time
from typing import Any

import httpx


class HackerOneAuthError(RuntimeError):
    """Raised when HackerOne authentication fails."""


class HackerOneAPIError(RuntimeError):
    """Raised when HackerOne API request fails."""


class HackerOneClient:
    """Async HackerOne API client for program/report workflows."""

    BASE_URL = "https://api.hackerone.com/v1"

    def __init__(
        self,
        *,
        username: str,
        api_token: str,
        timeout_seconds: float = 25.0,
        max_retries: int = 2,
        min_request_interval_seconds: float = 0.2,
    ) -> None:
        self.username = (username or "").strip()
        self.api_token = (api_token or "").strip()
        self.timeout_seconds = timeout_seconds
        self.max_retries = max_retries
        self.min_request_interval_seconds = max(0.0, min_request_interval_seconds)
        self._rate_lock = asyncio.Lock()
        self._last_request_at = 0.0

        if not self.username or not self.api_token:
            raise HackerOneAuthError("HackerOne credentials are required")

    def _headers(self) -> dict[str, str]:
        token = base64.b64encode(f"{self.username}:{self.api_token}".encode("utf-8")).decode("ascii")
        return {
            "Authorization": f"Basic {token}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

    async def _request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json_body: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        url = f"{self.BASE_URL}{path}"
        last_exc: Exception | None = None

        for attempt in range(self.max_retries + 1):
            try:
                await self._wait_for_rate_window()
                async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                    response = await client.request(
                        method,
                        url,
                        headers=self._headers(),
                        params=params,
                        json=json_body,
                    )

                if response.status_code in (401, 403):
                    raise HackerOneAuthError("Invalid HackerOne credentials or insufficient API access")

                response.raise_for_status()
                payload = response.json()
                if not isinstance(payload, dict):
                    raise HackerOneAPIError("Unexpected HackerOne API response format")
                return payload
            except (HackerOneAuthError, HackerOneAPIError):
                raise
            except Exception as exc:  # pragma: no cover
                last_exc = exc
                if attempt < self.max_retries:
                    await asyncio.sleep(0.5 * (attempt + 1))
                    continue
                raise HackerOneAPIError(f"HackerOne request failed: {exc}") from exc

        raise HackerOneAPIError(f"HackerOne request failed: {last_exc}")

    async def _wait_for_rate_window(self) -> None:
        """Simple client-side pacing to reduce accidental burst traffic."""
        if self.min_request_interval_seconds <= 0:
            return

        async with self._rate_lock:
            now = time.monotonic()
            delta = now - self._last_request_at
            if delta < self.min_request_interval_seconds:
                await asyncio.sleep(self.min_request_interval_seconds - delta)
            self._last_request_at = time.monotonic()

    async def authenticate(self) -> dict[str, Any]:
        """Validate credentials by requesting first page of programs."""
        payload = await self._request("GET", "/programs", params={"page[size]": 1, "page[number]": 1})
        return {
            "authenticated": True,
            "program_count_hint": len(payload.get("data", [])),
        }

    async def get_programs(self, page_size: int = 100, max_pages: int = 20) -> list[dict[str, Any]]:
        """Fetch all accessible programs with pagination."""
        programs: list[dict[str, Any]] = []

        for page in range(1, max_pages + 1):
            payload = await self._request(
                "GET",
                "/programs",
                params={"page[size]": max(1, min(page_size, 100)), "page[number]": page},
            )
            batch = payload.get("data", []) or []
            if not batch:
                break
            programs.extend(batch)

            links = payload.get("links") or {}
            if not links.get("next"):
                break

        return programs

    async def get_structured_scope(self, handle: str, page_size: int = 100, max_pages: int = 20) -> list[dict[str, Any]]:
        """Fetch structured scope for a program handle with pagination."""
        safe_handle = (handle or "").strip()
        if not safe_handle:
            return []

        scopes: list[dict[str, Any]] = []
        path = f"/programs/{safe_handle}/structured_scopes"

        for page in range(1, max_pages + 1):
            payload = await self._request(
                "GET",
                path,
                params={"page[size]": max(1, min(page_size, 100)), "page[number]": page},
            )
            batch = payload.get("data", []) or []
            if not batch:
                break
            scopes.extend(batch)

            links = payload.get("links") or {}
            if not links.get("next"):
                break

        return scopes

    async def submit_report(
        self,
        *,
        title: str,
        vulnerability_information: str,
        impact: str,
        severity_rating: str,
        team_handle: str,
        manual_approval: bool,
        draft_only: bool = True,
    ) -> dict[str, Any]:
        """Prepare or submit a report. Never submits without manual approval.

        If draft_only=True, returns a validated draft payload without submission.
        """
        if not manual_approval:
            raise HackerOneAPIError("Manual approval is required before report submission")

        body = {
            "data": {
                "type": "report",
                "attributes": {
                    "title": title.strip()[:255],
                    "vulnerability_information": vulnerability_information.strip()[:8000],
                    "impact": impact.strip()[:4000],
                    "severity_rating": severity_rating.strip().lower(),
                },
                "relationships": {
                    "team": {
                        "data": {
                            "type": "team",
                            "id": team_handle.strip(),
                        }
                    }
                },
            }
        }

        if draft_only:
            return {
                "status": "draft_ready",
                "manual_approval": True,
                "submitted": False,
                "payload": body,
            }

        payload = await self._request("POST", "/reports", json_body=body)
        report_data = payload.get("data", {})
        attrs = report_data.get("attributes", {})
        return {
            "status": "submitted",
            "manual_approval": True,
            "submitted": True,
            "report": {
                "id": report_data.get("id"),
                "title": attrs.get("title"),
                "state": attrs.get("state"),
                "severity": attrs.get("severity_rating", "unknown"),
            },
        }

    async def get_my_reports(self, page_size: int = 100, max_pages: int = 20) -> list[dict[str, Any]]:
        """Fetch authenticated user's reports with pagination."""
        reports: list[dict[str, Any]] = []
        for page in range(1, max_pages + 1):
            payload = await self._request(
                "GET",
                "/reports",
                params={"page[size]": max(1, min(page_size, 100)), "page[number]": page},
            )
            batch = payload.get("data", []) or []
            if not batch:
                break
            reports.extend(batch)

            links = payload.get("links") or {}
            if not links.get("next"):
                break

        return reports
