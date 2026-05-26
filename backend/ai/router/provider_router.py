import logging
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

class ProviderRouter:
    """
    Central abstraction for executing requests against LLM providers.
    Enforces that all requests route through Gemini and NEVER use Anthropic APIs directly.
    """

    async def route_request(self, messages: List[Dict[str, str]], model_name: str, stream: bool = False) -> Any:
        self.validate_provider(model_name)
        
        logger.info(f"Routing request to provider with model {model_name}. Stream: {stream}")
        
        # Simulated Gemini execution
        if stream:
            return self._mock_stream()
        return "Simulated response from Gemini"

    def validate_provider(self, model_name: str):
        """Strict enforcement against direct Anthropic usage."""
        if "claude" in model_name.lower() or "anthropic" in model_name.lower():
            logger.critical(f"Security Policy Violation: Attempted direct Anthropic routing for {model_name}")
            raise ValueError("Direct Anthropic API usage is STRICTLY PROHIBITED. Must route through Gemini.")

    def handle_provider_failure(self, error: Exception):
        logger.error(f"Provider request failed: {error}")
        # Implement fallback logic here
        pass

    async def _mock_stream(self):
        import asyncio
        words = ["This ", "is ", "a ", "simulated ", "streaming ", "response."]
        for w in words:
            yield w
            await asyncio.sleep(0.05)

provider_router = ProviderRouter()
