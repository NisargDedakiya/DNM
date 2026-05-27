from backend.ai.claude_client import claude
import logging
logger = logging.getLogger(__name__)

EXPLAIN_SYS = '''
Explain security scanner output in plain English for a CS student.
Return ONLY valid JSON array:
[{
  line: str,
  severity: critical|high|medium|low|info|noise,
  plain_english: str,
  action: str,
  likely_real: bool,
  confidence_pct: int
}]
'''

class OutputExplainer:
    async def explain(self, lines: list[str], tool: str) -> list[dict]:
        results: list[dict] = []
        for i in range(0, len(lines), 15):  # 15 lines per Claude call
            batch = lines[i:i+15]
            prompt = f'Tool: {tool} Output lines: ' + ' '.join(batch)
            try:
                r = await claude.analyze_json(prompt, EXPLAIN_SYS)
                if isinstance(r, list):
                    results.extend(r)
            except Exception as e:
                logger.error(f'Explain batch failed: {e}')
        return results

output_explainer = OutputExplainer()
