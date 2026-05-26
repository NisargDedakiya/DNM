import logging
from typing import List, Dict

logger = logging.getLogger(__name__)

class ContextWindow:
    """Manages the token window size for AI requests."""

    MAX_MESSAGES = 10

    def build_context_window(self, system_prompt: str, history: List[Dict[str, str]], current_query: str) -> List[Dict[str, str]]:
        """Assemble the final message array for the LLM."""
        messages = [{"role": "system", "content": system_prompt}]
        
        trimmed_history = self.trim_context(history)
        messages.extend(trimmed_history)
        
        messages.append({"role": "user", "content": current_query})
        return messages

    def prioritize_context(self, context_items: List[Dict[str, str]]) -> List[Dict[str, str]]:
        """Sort or filter items by relevance."""
        return context_items

    def trim_context(self, history: List[Dict[str, str]]) -> List[Dict[str, str]]:
        """Enforce maximum message counts to save tokens."""
        if len(history) > self.MAX_MESSAGES:
            logger.debug("Trimming context window to fit max messages.")
            return history[-self.MAX_MESSAGES:]
        return history

context_window = ContextWindow()
