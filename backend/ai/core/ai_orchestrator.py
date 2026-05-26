import logging
from typing import Dict, Any, List, AsyncGenerator
import json

from backend.ai.router.model_selector import model_selector
from backend.ai.router.provider_router import provider_router
from backend.ai.cache.ai_cache import ai_cache
from backend.ai.memory.context_window import context_window
from backend.ai.prompts.system_prompts import SystemPrompts

logger = logging.getLogger(__name__)

class AIOrchestrator:
    """Unified entry point for all AI execution in the platform."""

    async def generate_response(self, prompt: str, system_prompt: str = SystemPrompts.TRIAGE, task_type: str = "triage") -> str:
        """Standard synchronous response generation."""
        # 1. Check Cache
        cached = await ai_cache.retrieve_cached_response(prompt, system_prompt)
        if cached:
            logger.info("Cache hit for AI generation")
            return cached

        # 2. Select Model
        model = model_selector.select_model(task_type)
        
        # 3. Build Context Window
        messages = context_window.build_context_window(system_prompt, [], prompt)
        
        # 4. Route and Execute
        response = await provider_router.route_request(messages, model, stream=False)
        
        # 5. Cache result
        await ai_cache.cache_response(prompt, system_prompt, response)
        
        return response

    async def generate_stream(self, prompt: str, history: List[Dict[str, str]], system_prompt: str = SystemPrompts.HUNT_CHAT) -> AsyncGenerator[str, None]:
        """Streaming generation for chat."""
        model = model_selector.select_model("chat")
        messages = context_window.build_context_window(system_prompt, history, prompt)
        
        # Retrieve async generator
        stream = await provider_router.route_request(messages, model, stream=True)
        
        async for chunk in stream:
            yield chunk

    async def generate_json(self, prompt: str, schema: Dict[str, Any], system_prompt: str) -> Dict[str, Any]:
        """Force structured JSON output."""
        # Implementation depends on specific provider capabilities (e.g., Gemini structured output)
        logger.info("Generating structured JSON response")
        return {"status": "success", "mock": True}

ai_orchestrator = AIOrchestrator()
