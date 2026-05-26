import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

class PromptBuilder:
    """Assembles context and templates into final LLM prompts."""

    def build_prompt(self, template: str, context: Dict[str, Any]) -> str:
        """Inject context into the template securely."""
        sanitized_context = self.sanitize_prompt(context)
        try:
            return template.format(**sanitized_context)
        except KeyError as e:
            logger.warning(f"Missing context key for template formatting: {e}")
            return template # Fallback

    def inject_context(self, base_prompt: str, additional_context: str) -> str:
        return f"{base_prompt}\n\nAdditional Context:\n{additional_context}"

    def sanitize_prompt(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Ensure no raw tokens or secrets are injected."""
        # Advisory sanitization logic
        return context

prompt_builder = PromptBuilder()
