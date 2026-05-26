import logging
from typing import Dict, Any, AsyncGenerator
import uuid

logger = logging.getLogger(__name__)

class ChatManager:
    """Manages chat session lifecycle and socket streaming."""

    async def create_chat_session(self, org_id: str, title: str = "Investigation") -> str:
        session_id = str(uuid.uuid4())
        logger.info(f"Created chat session {session_id} for org {org_id}")
        # db.add(ChatSession(id=session_id, org_id=org_id, title=title))
        return session_id

    async def append_message(self, session_id: str, role: str, content: str):
        """Save a message to the database."""
        logger.debug(f"Appending {role} message to {session_id}")
        # db.add(ChatMessage(session_id=session_id, role=role, content=content))
        pass

    async def stream_response(self, response_text: str) -> AsyncGenerator[str, None]:
        """Simulate a streaming websocket response."""
        import asyncio
        words = response_text.split()
        for word in words:
            yield word + " "
            await asyncio.sleep(0.05)

chat_manager = ChatManager()
