from backend.ai.claude_client import claude

EXPLAIN_SYS = '''
Explain bug bounty scanner output in plain English for a CS student.
Return ONLY valid JSON array:
[{
  "line": "str",
  "severity": "critical|high|medium|low|info|noise",
  "plain_english": "str",
  "action": "str",
  "likely_real": true,
  "confidence_pct": 90
}]
'''

class OutputExplainer:
    async def explain(self, lines: list[str], tool: str) -> list[dict]:
        results = []
        for i in range(0, len(lines), 15):  # batches of 15
            batch = lines[i:i+15]
            prompt = f'Tool: {tool} Lines: ' + ' '.join(batch)
            try:
                r = await claude.analyze_json(prompt, EXPLAIN_SYS)
                if isinstance(r, list):
                    results.extend(r)
            except Exception:
                pass
        return results

output_explainer = OutputExplainer()
