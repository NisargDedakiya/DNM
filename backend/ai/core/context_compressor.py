import logging
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

class ContextCompressor:
    """Optimizes context size to reduce token consumption."""

    def compress_context(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Reduce size of context payloads before feeding to LLM."""
        compressed = {}
        if "findings" in context:
            compressed["findings"] = self.summarize_findings(context["findings"])
        if "history" in context:
            compressed["history"] = self.optimize_token_usage(context["history"])
        return compressed

    def summarize_findings(self, findings: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Extract only critical fields from findings to save tokens."""
        summary = []
        for f in findings:
            summary.append({
                "title": f.get("title"),
                "severity": f.get("severity"),
                "target": f.get("target")
            })
        return summary

    def optimize_token_usage(self, history: List[Dict[str, str]]) -> List[Dict[str, str]]:
        """Keep only recent messages or summarize older ones."""
        # Advisory: return last 5 messages
        return history[-5:] if len(history) > 5 else history

context_compressor = ContextCompressor()
