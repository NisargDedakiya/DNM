import logging
import time
from typing import Dict, Any, List, AsyncGenerator
import json
from uuid import UUID

from backend.ai.router.model_selector import model_selector
from backend.ai.router.provider_router import provider_router
from backend.ai.cache.ai_cache import ai_cache
from backend.ai.memory.context_window import context_window
from backend.ai.prompts.system_prompts import SystemPrompts
from backend.ai.core.prompt_optimizer import prompt_optimizer
from backend.ai.core.ai_metrics import AIMetrics
from backend.ai.history.context_recall import ContextRecall
from backend.database.session import AsyncSessionLocal

logger = logging.getLogger(__name__)

class AIOrchestrator:
    """Unified entry point for all AI execution with memory recall injection."""

    async def generate_response(self, prompt: str, system_prompt: str = SystemPrompts.TRIAGE, task_type: str = "triage", org_id: str = "system") -> str:
        """Standard synchronous response generation with context-aware memory retrieval."""
        # 1. Retrieve Historical Context
        recalled_context = ""
        try:
            uuid_org = UUID(org_id)
            async with AsyncSessionLocal() as db:
                recall = ContextRecall(db)
                findings = await recall.recall_similar_findings(uuid_org, prompt, limit=3)
                if findings:
                    recalled_context = "\n[Historical Context: Similar Prior Findings]\n" + json.dumps(findings)
        except ValueError:
            pass # org_id is not a valid UUID format (e.g. "system")
        except Exception as e:
            logger.warning(f"Failed to recall context for AI query: {e}")

        # 2. Optimize / Compress Prompt
        optimized_prompt = prompt_optimizer.compress_prompt(prompt + recalled_context)
        
        # 3. Check Cache
        cached = await ai_cache.retrieve_cached_response(optimized_prompt, system_prompt)
        if cached:
            logger.info("Cache hit for AI generation")
            await AIMetrics.record_cache_event(hit=True, org_id=org_id)
            return cached

        await AIMetrics.record_cache_event(hit=False, org_id=org_id)

        # 4. Select Model
        model = model_selector.select_model(task_type)
        
        # 5. Build Context Window
        messages = context_window.build_context_window(system_prompt, [], optimized_prompt)
        
        # 6. Route and Execute
        response = await provider_router.route_request(messages, model, stream=False, org_id=org_id)
        
        # 7. Cache result
        await ai_cache.cache_response(optimized_prompt, system_prompt, response)
        
        return response

    async def generate_stream(self, prompt: str, history: List[Dict[str, str]], system_prompt: str = SystemPrompts.HUNT_CHAT, org_id: str = "system") -> AsyncGenerator[str, None]:
        """Streaming generation for chat."""
        optimized_prompt = prompt_optimizer.compress_prompt(prompt)
        model = model_selector.select_model("chat")
        messages = context_window.build_context_window(system_prompt, history, optimized_prompt)
        
        # Retrieve async generator
        stream = await provider_router.route_request(messages, model, stream=True, org_id=org_id)
        
        async for chunk in stream:
            yield chunk

    async def generate_json(self, prompt: str, schema: Dict[str, Any], system_prompt: str, org_id: str = "system") -> Dict[str, Any]:
        """Force structured JSON output."""
        logger.info("Generating structured JSON response")
        optimized_prompt = prompt_optimizer.compress_prompt(prompt)
        model = model_selector.select_model("triage")
        messages = context_window.build_context_window(system_prompt, [], optimized_prompt)
        
        response = await provider_router.route_request(messages, model, stream=False, org_id=org_id)
        try:
            return json.loads(response)
        except Exception:
            return {"status": "success", "data": response}

ai_orchestrator = AIOrchestrator()


