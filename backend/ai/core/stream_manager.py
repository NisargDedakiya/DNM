import logging
from typing import AsyncGenerator

logger = logging.getLogger(__name__)

class StreamManager:
    """Manages streaming responses and WebSocket compatibility."""

    async def stream_response(self, text_stream: AsyncGenerator[str, None], session_id: str) -> AsyncGenerator[str, None]:
        """Wrap the stream, logging and handling lifecycle."""
        logger.debug(f"Starting stream for session {session_id}")
        try:
            async for chunk in text_stream:
                yield self.handle_stream_chunk(chunk)
        finally:
            self.finalize_stream(session_id)

    def handle_stream_chunk(self, chunk: str) -> str:
        """Process and format individual stream chunks for frontend consumption."""
        return chunk

    def finalize_stream(self, session_id: str):
        """Cleanup logic when stream finishes or errors."""
        logger.debug(f"Finalized stream for session {session_id}")

stream_manager = StreamManager()
