import logging
from typing import Dict, Any, AsyncGenerator

from backend.ai.core.ai_orchestrator import ai_orchestrator
from backend.ai.prompts.system_prompts import SystemPrompts
from backend.ai.core.stream_manager import stream_manager

logger = logging.getLogger(__name__)

class AIService:
    """Application-level service bridging business logic and AI Orchestrator."""

    async def analyze_finding(self, finding_data: Dict[str, Any]) -> str:
        logger.info(f"Analyzing finding: {finding_data.get('title')}")
        prompt = f"Analyze: {finding_data}"
        return await ai_orchestrator.generate_response(prompt, SystemPrompts.TRIAGE, task_type="triage")

    async def generate_report(self, findings: list) -> str:
        logger.info("Generating full executive report")
        prompt = f"Generate report for {len(findings)} findings."
        return await ai_orchestrator.generate_response(prompt, SystemPrompts.REPORT_WRITER, task_type="report")

    async def explain_attack_chain(self, chain_data: Dict[str, Any]) -> str:
        logger.info("Explaining attack chain")
        prompt = f"Explain chain: {chain_data}"
        return await ai_orchestrator.generate_response(prompt, SystemPrompts.ATTACK_GRAPH, task_type="triage")

    async def generate_hunt_chat_stream(self, query: str, session_id: str, history: list) -> AsyncGenerator[str, None]:
        """Stream a chat response through the StreamManager."""
        logger.info(f"Generating chat stream for session {session_id}")
        
        raw_stream = ai_orchestrator.generate_stream(query, history, SystemPrompts.HUNT_CHAT)
        
        async for formatted_chunk in stream_manager.stream_response(raw_stream, session_id):
            yield formatted_chunk

ai_service = AIService()
