import logging
from typing import Any, Dict
from backend.websocket.manager import websocket_manager
from backend.core.events import EventType

logger = logging.getLogger(__name__)

class WebsocketPublisher:
    """Transforms and publishes internal events to connected websocket clients."""
    
    async def publish_scan_update(self, org_id: str, payload: Dict[str, Any]):
        event = {
            "type": "SCAN_UPDATE",
            "data": payload
        }
        await websocket_manager.send_to_org(org_id, event)
        
    async def publish_finding_update(self, org_id: str, payload: Dict[str, Any]):
        event = {
            "type": "FINDING_UPDATE",
            "data": payload
        }
        await websocket_manager.send_to_org(org_id, event)
        
    async def publish_alert(self, org_id: str, payload: Dict[str, Any]):
        event = {
            "type": "CRITICAL_ALERT",
            "data": payload
        }
        await websocket_manager.send_to_org(org_id, event)
        
    async def process_redis_event(self, event_type: str, org_id: str, payload: Dict[str, Any]):
        """Route Redis events to the correct websocket topic."""
        if event_type in [EventType.SCAN_STARTED, EventType.SCAN_PROGRESS, EventType.SCAN_COMPLETED]:
            await self.publish_scan_update(org_id, payload)
        elif event_type in [EventType.FINDING_CREATED, EventType.FINDING_TRIAGED]:
            await self.publish_finding_update(org_id, payload)
        elif event_type == EventType.FINDING_P1_ALERT:
            await self.publish_alert(org_id, payload)
        else:
            # Generic broadcast for other events
            event_name = event_type.value if hasattr(event_type, "value") else str(event_type)
            await websocket_manager.send_to_org(org_id, {"type": event_name, "data": payload})

ws_publisher = WebsocketPublisher()
