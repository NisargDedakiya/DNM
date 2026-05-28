import logging
from typing import Dict, Any, Optional
from backend.events.event_schema import EventType, BaseEvent, EventMetadata
from backend.events.redis_event_bus import redis_event_bus
from backend.events.correlation_manager import CorrelationManager
from backend.events.websocket_contracts import WebSocketContracts
from backend.websocket.publisher import ws_publisher

logger = logging.getLogger(__name__)

class EventService:
    """Centralized event orchestration and publishing using the event system upgrade."""
    
    STREAM_NAME = "nisarghunter_events"

    async def emit_event(self, event_type: EventType, org_id: str, payload: Dict[str, Any], user_id: Optional[str] = None):
        """Core method to wrap and publish an event to Redis and Websockets."""
        correlation_id = CorrelationManager.get_correlation_id()
        span_id = CorrelationManager.get_span_id()
        parent_span_id = CorrelationManager.get_parent_span_id()

        metadata = EventMetadata(
            version="v1",
            correlation_id=correlation_id,
            span_id=span_id,
            parent_span_id=parent_span_id
        )

        event = BaseEvent(
            event_type=event_type,
            org_id=org_id,
            user_id=user_id,
            metadata=metadata,
            payload=payload
        )
        
        # 1. Publish to Redis Stream
        try:
            await redis_event_bus.publish_event(self.STREAM_NAME, event)
        except Exception as e:
            logger.error(f"Failed to publish event to Redis stream: {e}")
            
        # 2. Push to websocket clients using normalized WebSocketContracts
        try:
            ws_payload = WebSocketContracts.normalize_payload(event)
            # Route through websocket publisher
            await ws_publisher.process_redis_event(event_type, org_id, ws_payload["data"])
        except Exception as e:
            logger.error(f"Failed to publish websocket event: {e}")
        
        logger.info(f"Emitted event {event_type} for org {org_id} (correlation_id: {correlation_id})")

    async def emit_scan_event(self, org_id: str, scan_id: str, target: str, status: str, progress: int = 0, metadata: dict = None):
        if status == "starting":
            evt = EventType.SCAN_STARTED
        elif status == "completed" or status == "failed":
            evt = EventType.SCAN_COMPLETED
        else:
            evt = EventType.SCAN_PROGRESS
            
        payload = {
            "scan_id": scan_id,
            "target": target,
            "status": status,
            "progress": progress,
            "metadata": metadata or {}
        }
        await self.emit_event(evt, org_id, payload)

    async def emit_finding_event(self, event_type: EventType, org_id: str, payload: Dict[str, Any]):
        await self.emit_event(event_type, org_id, payload)

    async def emit_alert_event(self, org_id: str, payload: Dict[str, Any]):
        await self.emit_event(EventType.FINDING_P1_ALERT, org_id, payload)

event_service = EventService()

