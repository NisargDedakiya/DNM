import logging
from typing import Dict, Any
from fastapi import HTTPException

logger = logging.getLogger(__name__)

class EventIsolationGuard:
    """Enforces org boundaries on Redis streams and websocket payloads."""

    def validate_event_scope(self, event_org_id: str, consumer_org_id: str):
        """Ensure a worker or websocket only consumes events for its org."""
        if event_org_id != consumer_org_id:
            logger.error(f"Event scope violation! Event org: {event_org_id}, Consumer org: {consumer_org_id}")
            raise PermissionError("Cross-org event consumption blocked.")

    def isolate_org_events(self, stream_name: str, org_id: str) -> str:
        """Namespace Redis streams by org to guarantee isolation at the messaging layer."""
        return f"{stream_name}:{org_id}"

    def sanitize_event_payload(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Strip sensitive internal metadata before publishing to websockets."""
        safe_payload = payload.copy()
        safe_payload.pop("internal_worker_id", None)
        safe_payload.pop("db_connection_string", None)
        return safe_payload

event_guard = EventIsolationGuard()
