"""
Webhook registration and signed delivery helpers.
"""
from __future__ import annotations

import asyncio
import hashlib
import hmac
import json
import logging
import secrets
from dataclasses import dataclass
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from backend.models.webhook_subscription import WebhookSubscription

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class WebhookDeliveryResult:
    success: bool
    status_code: int | None
    attempts: int
    endpoint: str
    error: str | None = None


class WebhookManager:
    def __init__(self, db: AsyncSession | None = None):
        self.db = db

    async def register_webhook(
        self,
        organization_id: UUID,
        endpoint: str,
        subscribed_events: list[str] | None,
        secret: str | None = None,
    ) -> dict[str, Any]:
        webhook_secret = secret or secrets.token_urlsafe(32)
        subscription = WebhookSubscription(
            organization_id=organization_id,
            endpoint=endpoint,
            subscribed_events=subscribed_events or [],
            secret=webhook_secret,
        )
        if self.db is not None:
            self.db.add(subscription)
            await self.db.commit()
            await self.db.refresh(subscription)
        return {
            "id": subscription.id,
            "organization_id": subscription.organization_id,
            "endpoint": subscription.endpoint,
            "subscribed_events": subscription.subscribed_events or [],
            "secret": webhook_secret,
            "created_at": subscription.created_at,
        }

    def validate_signature(self, payload: bytes | str, signature: str, secret: str) -> bool:
        body = payload.encode("utf-8") if isinstance(payload, str) else payload
        expected = hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
        return hmac.compare_digest(expected, signature)

    async def retry_failed_delivery(
        self,
        endpoint: str,
        payload: dict[str, Any],
        secret: str,
        max_attempts: int = 3,
        timeout_seconds: int = 10,
    ) -> WebhookDeliveryResult:
        body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
        signature = hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()

        last_error: str | None = None
        status_code: int | None = None
        for attempt in range(1, max_attempts + 1):
            try:
                request = Request(
                    endpoint,
                    data=body,
                    headers={
                        "Content-Type": "application/json",
                        "X-NisargHunter-Signature": signature,
                    },
                    method="POST",
                )

                response = await asyncio.to_thread(
                    lambda: urlopen(request, timeout=timeout_seconds),
                )
                status_code = getattr(response, "status", 200)
                return WebhookDeliveryResult(True, status_code, attempt, endpoint)
            except HTTPError as exc:
                last_error = f"HTTP {exc.code}: {exc.reason}"
                status_code = exc.code
            except URLError as exc:
                last_error = str(exc.reason)
            except Exception as exc:
                last_error = str(exc)

            logger.warning("Webhook delivery failed attempt %s to %s: %s", attempt, endpoint, last_error)
            if attempt < max_attempts:
                await asyncio.sleep(min(2**attempt, 5))

        return WebhookDeliveryResult(False, status_code, max_attempts, endpoint, last_error)

    async def list_subscriptions(self, organization_id: UUID) -> list[WebhookSubscription]:
        if self.db is None:
            return []
        result = await self.db.execute(
            select(WebhookSubscription).where(WebhookSubscription.organization_id == organization_id),
        )
        return list(result.scalars().all())
