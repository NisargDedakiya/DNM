from typing import Dict, Type
from backend.events.event_schema import EventType, BaseEvent

class EventRegistry:
    """Central registry mapping EventTypes to their structures and metadata."""
    
    def __init__(self):
        self._registry: Dict[EventType, Type[BaseEvent]] = {}

    def register(self, event_type: EventType, schema_cls: Type[BaseEvent]):
        self._registry[event_type] = schema_cls

    def get_schema(self, event_type: EventType) -> Type[BaseEvent]:
        return self._registry.get(event_type, BaseEvent)

event_registry = EventRegistry()
