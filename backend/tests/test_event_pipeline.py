import pytest
import asyncio
from unittest.mock import AsyncMock, patch
from backend.events.event_schema import EventType, BaseEvent, EventMetadata
from backend.events.redis_event_bus import redis_event_bus
from backend.events.correlation_manager import CorrelationManager

@pytest.mark.asyncio
async def test_correlation_id_propagation():
    """Verify that CorrelationManager correctly sets and propagates correlation IDs across context blocks."""
    CorrelationManager.clear()
    
    correlation_id = CorrelationManager.initialize_context(correlation_id="test-correlation-123")
    assert correlation_id == "test-correlation-123"
    assert CorrelationManager.get_correlation_id() == "test-correlation-123"
    
    async def sub_task():
        return CorrelationManager.get_correlation_id()
        
    result = await asyncio.create_task(sub_task())
    assert result == "test-correlation-123"
    CorrelationManager.clear()

@pytest.mark.asyncio
async def test_redis_event_bus_deduplication():
    """Verify that identical events published to the bus within the TTL window are deduplicated and dropped."""
    # Use unittest.mock to patch redis client calls
    mock_redis = AsyncMock()
    # First set returns True (nx=True), second returns False (already exists)
    mock_redis.set.side_effect = [True, False]
    mock_redis.xadd.return_value = "12345-0"
    
    with patch.object(redis_event_bus, "redis", mock_redis), \
         patch.object(redis_event_bus, "connect", AsyncMock()):
         
        metadata = EventMetadata(
            version="v1",
            correlation_id="test-correlation-123"
        )
        
        event = BaseEvent(
            event_id="unique-event-id-999",
            event_type=EventType.SCAN_STARTED,
            org_id="org-1",
            metadata=metadata,
            payload={"scan_id": "scan-1", "target": "example.com"}
        )
        
        res1 = await redis_event_bus.publish_event("test_stream", event)
        res2 = await redis_event_bus.publish_event("test_stream", event)
        
        assert res1 == "12345-0"
        assert res2 == "duplicate"

