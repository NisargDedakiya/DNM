import logging
from typing import Dict, Any, Optional
from backend.core.events import EventType, BaseEvent
from backend.core.redis_streams import redis_streams
from backend.websocket.publisher import ws_publisher

logger = logging.getLogger(__name__)

class EventService:
    """Centralized event orchestration and publishing."""
    
    STREAM_NAME = "nisarghunter_events"

    async def emit_event(self, event_type: EventType, org_id: str, payload: Dict[str, Any], user_id: Optional[str] = None):
        """Core method to wrap and publish an event to Redis and Websockets."""
        event = BaseEvent(
            event_type=event_type,
            org_id=org_id,
            user_id=user_id,
            payload=payload
        )
        
        event_dict = event.model_dump()
        event_dict["timestamp"] = event.timestamp.isoformat()
        
        # 1. Publish to Redis Stream (for worker consumption, auditing)
        try:
            await redis_streams.publish_event(self.STREAM_NAME, event_dict)
        except Exception as e:
            logger.error(f"Failed to publish event to Redis stream: {e}")
            
        # 2. Immediately push to active websocket clients for real-time UI
        try:
            await ws_publisher.process_redis_event(event_type, org_id, payload)
        except Exception as e:
            logger.error(f"Failed to publish websocket event: {e}")
        
        logger.info(f"Emitted event {event_type} for org {org_id}")

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
