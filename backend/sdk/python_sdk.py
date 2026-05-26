"""
Developer-friendly Python SDK for public APIs and realtime events.
"""
from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass
from typing import Any, AsyncIterator
from urllib.request import Request, urlopen


@dataclass(slots=True)
class SDKConfig:
    base_url: str
    api_key: str | None = None
    websocket_url: str | None = None


class NisargHunterPythonSDK:
    def __init__(self, base_url: str, api_key: str | None = None, websocket_url: str | None = None):
        self.config = SDKConfig(base_url.rstrip("/"), api_key, websocket_url)

    def authenticate(self, api_key: str) -> "NisargHunterPythonSDK":
        self.config.api_key = api_key
        return self

    def _headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.config.api_key:
            headers["X-API-Key"] = self.config.api_key
        return headers

    def _request(self, path: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        body = None if payload is None else json.dumps(payload).encode("utf-8")
        request = Request(
            f"{self.config.base_url}{path}",
            data=body,
            headers=self._headers(),
            method="POST" if payload is not None else "GET",
        )
        response = urlopen(request, timeout=30)
        return json.loads(response.read().decode("utf-8"))

    def _get(self, path: str, params: dict[str, Any]) -> dict[str, Any]:
        from urllib.parse import urlencode

        query = urlencode(params)
        request = Request(f"{self.config.base_url}{path}?{query}", headers=self._headers(), method="GET")
        response = urlopen(request, timeout=30)
        return json.loads(response.read().decode("utf-8"))

    def get_findings(self, organization_id: str, page: int = 1, page_size: int = 20) -> dict[str, Any]:
        return self._get(
            "/public/findings",
            {"organization_id": organization_id, "page": page, "page_size": page_size},
        )

    def get_attack_paths(self, organization_id: str, page: int = 1, page_size: int = 20) -> dict[str, Any]:
        return self._get(
            "/public/attack-paths",
            {"organization_id": organization_id, "page": page, "page_size": page_size},
        )

    async def subscribe_to_events(self, websocket_path: str = "/ws/public-events") -> AsyncIterator[dict[str, Any]]:
        websocket_url = self.config.websocket_url or self.config.base_url.replace("https://", "wss://").replace("http://", "ws://")
        websocket_url = f"{websocket_url.rstrip('/')}{websocket_path}"

        try:
            import websockets  # type: ignore
        except Exception:
            while True:
                await asyncio.sleep(5)
                yield {"event": "poll", "message": "websockets package not installed"}

        async with websockets.connect(websocket_url, extra_headers=self._headers()) as socket:  # type: ignore[attr-defined]
            while True:
                message = await socket.recv()
                yield json.loads(message)


def authenticate(base_url: str, api_key: str, websocket_url: str | None = None) -> NisargHunterPythonSDK:
    return NisargHunterPythonSDK(base_url, api_key=api_key, websocket_url=websocket_url)


def get_findings(client: NisargHunterPythonSDK, organization_id: str, page: int = 1, page_size: int = 20) -> dict[str, Any]:
    return client.get_findings(organization_id, page=page, page_size=page_size)


def get_attack_paths(client: NisargHunterPythonSDK, organization_id: str, page: int = 1, page_size: int = 20) -> dict[str, Any]:
    return client.get_attack_paths(organization_id, page=page, page_size=page_size)


async def subscribe_to_events(client: NisargHunterPythonSDK, websocket_path: str = "/ws/public-events") -> AsyncIterator[dict[str, Any]]:
    async for event in client.subscribe_to_events(websocket_path=websocket_path):
        yield event
