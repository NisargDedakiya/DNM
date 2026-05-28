import logging
import time
from typing import Dict, Any, List
from backend.ai.core.ai_budget_manager import ai_budget_manager
from backend.ai.core.ai_metrics import AIMetrics

logger = logging.getLogger(__name__)

class ProviderRouter:
    """
    Central abstraction for executing requests against LLM providers.
    Enforces that all requests route through Gemini and NEVER use Anthropic APIs directly.
    """

    async def route_request(self, messages: List[Dict[str, str]], model_name: str, stream: bool = False, org_id: str = "system") -> Any:
        self.validate_provider(model_name)
        
        # 1. Estimate prompt tokens
        total_input_len = sum(len(msg.get("content", "")) for msg in messages)
        estimated_input_tokens = max(1, total_input_len // 4)
        
        # 2. Enforce budget limits
        budget_ok = await ai_budget_manager.check_budget(org_id, estimated_input_tokens)
        if not budget_ok:
            raise ValueError(f"AI Budget exceeded for organization {org_id}. Request blocked.")

        logger.info(f"Routing request to provider with model {model_name}. Stream: {stream}")
        
        start_time = time.time()
        
        if stream:
            # For stream, record budget on completion
            await ai_budget_manager.record_usage(org_id, estimated_input_tokens, 20)
            await AIMetrics.record_tokens(model_name, estimated_input_tokens, 20, org_id)
            await AIMetrics.record_latency(model_name, 0.5, org_id)
            return self._mock_stream()

        # Simulated response latency
        response_text = "Simulated response from Gemini"
        estimated_output_tokens = len(response_text) // 4
        
        duration = time.time() - start_time
        
        # Record actual token metrics and usage billing
        await ai_budget_manager.record_usage(org_id, estimated_input_tokens, estimated_output_tokens)
        await AIMetrics.record_tokens(model_name, estimated_input_tokens, estimated_output_tokens, org_id)
        await AIMetrics.record_latency(model_name, duration, org_id)

        return response_text

    def validate_provider(self, model_name: str):
        """Strict enforcement against direct Anthropic usage."""
        if "claude" in model_name.lower() or "anthropic" in model_name.lower():
            logger.critical(f"Security Policy Violation: Attempted direct Anthropic routing for {model_name}")
            raise ValueError("Direct Anthropic API usage is STRICTLY PROHIBITED. Must route through Gemini.")

    def handle_provider_failure(self, error: Exception):
        logger.error(f"Provider request failed: {error}")
        # Fallback logic
        pass

    async def _mock_stream(self):
        import asyncio
        words = ["This ", "is ", "a ", "simulated ", "streaming ", "response."]
        for w in words:
            yield w
            await asyncio.sleep(0.05)

provider_router = ProviderRouter()

