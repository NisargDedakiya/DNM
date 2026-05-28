import logging
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

class PromptOptimizer:
    """Enterprise prompt optimizer using compression, structural truncation, and dynamic variables."""

    def compress_prompt(self, prompt: str) -> str:
        """Strip redundant whitespace, conversational filler, and structure prompts compactly."""
        lines = [line.strip() for line in prompt.split("\n")]
        # Remove empty lines and leading spaces
        cleaned = [line for line in lines if line]
        compressed = " ".join(cleaned)
        
        # Strip common AI conversational padding to enforce high-density directives
        replacements = {
            "please analyze the following": "Analyze:",
            "could you write a report on": "Write report:",
            "make sure to include": "Include:",
            "under the hood": "internals",
        }
        for match, replacement in replacements.items():
            compressed = compressed.replace(match, replacement)
            
        logger.debug(f"Compressed prompt from {len(prompt)} to {len(compressed)} chars.")
        return compressed

    def format_triage_context(self, finding_title: str, severity: str, evidence: str) -> str:
        """Dynamically builds compressed structural payloads to bypass high context bounds."""
        truncated_evidence = evidence[:1500] if evidence else "No evidence provided."
        return (
            f"Triage Finding:\n"
            f"Title: {finding_title}\n"
            f"Severity: {severity}\n"
            f"Evidence: {truncated_evidence}"
        )

prompt_optimizer = PromptOptimizer()
