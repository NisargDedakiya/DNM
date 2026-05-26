import logging

logger = logging.getLogger(__name__)

class ModelSelector:
    """Intelligently routes tasks to the appropriate model based on task complexity."""

    def select_model(self, task_type: str) -> str:
        """
        Routing logic mapping capabilities to provider-agnostic identifiers.
        """
        logger.debug(f"Selecting model for task: {task_type}")
        
        if task_type == "chat":
            return "gemini-1.5-flash"  # Fast for realtime chat
        elif task_type == "report":
            return "gemini-1.5-pro"    # Strong reasoning for reports
        elif task_type == "triage":
            return "gemini-1.5-flash"  # Balanced for rapid triage
        
        return "gemini-1.5-flash"      # Default fallback

model_selector = ModelSelector()
