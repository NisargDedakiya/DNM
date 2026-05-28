from typing import Dict, Any
from backend.events.event_schema import BaseEvent

class WebSocketContracts:
    """Standardizes envelope structures sent over WebSockets to frontend."""
    
    @staticmethod
    def normalize_payload(event: BaseEvent) -> Dict[str, Any]:
        """Convert a BaseEvent into a standard UI-compatible WebSocket message."""
        # Mapping to frontend-compatible upper case message types
        type_mapping = {
            "scan.started": "SCAN_UPDATE",
            "scan.progress": "SCAN_UPDATE",
            "scan.completed": "SCAN_UPDATE",
            "scan.failed": "SCAN_UPDATE",
            "finding.created": "FINDING_UPDATE",
            "finding.triaged": "FINDING_UPDATE",
            "finding.p1_alert": "CRITICAL_ALERT",
            "trace.started": "TRACE_UPDATE",
            "trace.completed": "TRACE_UPDATE",
        }
        
        event_str = event.event_type.value if hasattr(event.event_type, "value") else str(event.event_type)
        ws_type = type_mapping.get(event_str, event_str.upper().replace(".", "_"))
        
        return {
            "type": ws_type,
            "event_type": event_str,
            "event_id": event.event_id,
            "org_id": event.org_id,
            "user_id": event.user_id,
            "timestamp": event.timestamp.isoformat() if hasattr(event.timestamp, "isoformat") else str(event.timestamp),
            "correlation_id": event.metadata.correlation_id,
            "data": event.payload
        }
