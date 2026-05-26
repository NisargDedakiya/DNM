"""
Async-safe event dispatcher for webhook and realtime delivery.
"""
from __future__ import annotations

import asyncio
import logging
from typing import Any
from uuid import UUID

from backend.core.events import EventType
from backend.webhooks.webhook_manager import WebhookManager

logger = logging.getLogger(__name__)

SUPPORTED_EVENTS = {
    EventType.FINDING_P1_ALERT.value,
    EventType.EXPOSURE_DRIFT.value,
    EventType.MONITORING_HEALTH_UPDATED.value,
    EventType.TELEMETRY_EVENT.value,
    "attack-path.escalation",
    "exposure.anomaly",
}


class EventDispatcher:
    def __init__(self, webhook_manager: WebhookManager | None = None):
        self.webhook_manager = webhook_manager or WebhookManager()

    def _matches(self, subscription_events: list[str] | None, event_type: str) -> bool:
        if not subscription_events:
            return True
        normalized = {event.lower() for event in subscription_events}
        return event_type.lower() in normalized or "*" in normalized

    def _build_payload(self, organization_id: UUID, event_type: str, payload: dict[str, Any]) -> dict[str, Any]:
        return {
            "organization_id": str(organization_id),
            "event_type": event_type,
            "payload": payload,
        }

    async def dispatch_event(
        self,
        organization_id: UUID,
        event_type: str,
        payload: dict[str, Any],
        subscriptions: list[Any] | None = None,
    ) -> list[dict[str, Any]]:
        if event_type not in SUPPORTED_EVENTS:
            logger.debug("Skipping unsupported event type %s", event_type)
            return []

        if subscriptions is None:
            subscriptions = await self.webhook_manager.list_subscriptions(organization_id)

        delivery_payload = self._build_payload(organization_id, event_type, payload)

        deliveries = []
        for subscription in subscriptions:
            if str(subscription.organization_id) != str(organization_id):
                continue
            if not self._matches(subscription.subscribed_events, event_type):
                continue
            deliveries.append(
                self.webhook_manager.retry_failed_delivery(
                    endpoint=subscription.endpoint,
                    payload=delivery_payload,
                    secret=subscription.secret,
                ),
            )

        if not deliveries:
            return []

        results = await asyncio.gather(*deliveries, return_exceptions=True)
        serialized: list[dict[str, Any]] = []
        for result in results:
            if isinstance(result, Exception):
                logger.error("Webhook dispatch error: %s", result)
                continue
            serialized.append(
                {
                    "success": result.success,
                    "status_code": result.status_code,
                    "attempts": result.attempts,
                    "endpoint": result.endpoint,
                    "error": result.error,
                },
            )
        return serialized
