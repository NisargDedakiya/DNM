import logging
from typing import Dict, Any
from backend.ai.hunt_chat.hunt_chat_engine import hunt_chat_engine
from backend.chat.chat_manager import chat_manager
from backend.chat.chat_memory import chat_memory
from backend.websocket.manager import websocket_manager

logger = logging.getLogger(__name__)

class HuntChatService:
    """Orchestrates AI chat workflows and integrates backend intelligence."""

    async def process_chat_message(self, org_id: str, session_id: str, message: str) -> str:
        """Process incoming chat, generate AI response, and manage memory."""
        logger.info(f"Processing chat message for session {session_id}")
        
        # 1. Save User Message
        await chat_manager.append_message(session_id, "user", message)
        
        # 2. Retrieve history (token optimized)
        history = chat_memory.retrieve_relevant_context(session_id, message)
        
        # 3. Generate Insights (AI Engine)
        response_text = await hunt_chat_engine.process_hunt_query(org_id, message)
        
        # 4. Save AI Response
        await chat_manager.append_message(session_id, "assistant", response_text)
        
        return response_text

    async def enrich_chat_context(self, org_id: str) -> Dict[str, Any]:
        """Fetch real-time data to enrich AI prompt without user asking."""
        # e.g., pull latest report summaries
        return {"latest_activity": "Scan finished 5 mins ago."}

    async def generate_hunt_insights(self, org_id: str) -> str:
        """Proactive AI insight generation (no user prompt needed)."""
        return "I noticed 3 new high-severity findings. Would you like me to analyze them?"

hunt_chat_service = HuntChatService()
