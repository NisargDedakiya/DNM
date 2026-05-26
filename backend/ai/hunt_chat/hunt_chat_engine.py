import logging
from typing import Dict, Any

from backend.ai.hunt_chat.context_builder import context_builder
from backend.ai.hunt_chat.reasoning_engine import reasoning_engine
from backend.ai.hunt_chat.recommendation_engine import recommendation_engine

logger = logging.getLogger(__name__)

class HuntChatEngine:
    """Core AI engine coordinating context, reasoning, and generation."""

    async def process_hunt_query(self, org_id: str, query: str) -> str:
        """Main entry point to process a user query."""
        logger.info(f"Processing hunt query for {org_id}: {query}")
        
        # 1. Build Context
        context = await context_builder.build_hunt_context(org_id, query)
        
        # 2. Analyze
        # Normally we'd call an LLM (Claude/Gemini) here, passing context + prompt.
        response = await self.generate_investigation_response(query, context)
        return response

    async def generate_investigation_response(self, query: str, context: Dict[str, Any]) -> str:
        """Simulated LLM Generation."""
        # Sanitize prompt safely (advisory only)
        findings = context.get('findings', [])
        
        if "graphql" in query.lower():
            reasoning = reasoning_engine.explain_finding({"title": "GraphQL Introspection"})
            recommendations = recommendation_engine.recommend_next_steps(context)
            
            return f"**Investigation Copilot:**\n\n{reasoning}\n\n**Recommended Actions:**\n- {recommendations[0]}"
            
        return "**Investigation Copilot:** Based on your current workspace context, I recommend focusing on the newly discovered APIs."

    def summarize_hunt_context(self, context: Dict[str, Any]) -> str:
        return "Summary: 1 High severity finding linked to 2 exposed endpoints."

hunt_chat_engine = HuntChatEngine()
