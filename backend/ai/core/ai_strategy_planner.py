import logging
import json
from typing import Dict, Any, List
from uuid import UUID

from backend.ai.core.ai_orchestrator import ai_orchestrator
from backend.ai.prompts.system_prompts import SystemPrompts
from backend.database.session import AsyncSessionLocal
from backend.ai.history.context_recall import ContextRecall

logger = logging.getLogger(__name__)

class AIStrategyPlanner:
    """
    Autonomous attack surface strategist planning prioritized campaigns.
    Formulates strategic target sequences based on history, tech stacks, and priority score metrics.
    """

    async def generate_hunt_plan(self, org_id: str, program_name: str, tech_stack: str, live_endpoints: List[str]) -> Dict[str, Any]:
        """
        Formulate a step-by-step target sequence plan for hunting activities.
        Injects context memory to prevent repeating failed paths and focuses on high-value trust boundaries.
        """
        logger.info(f"Generating autonomous hunt plan for program: {program_name}")
        
        # 1. Fetch related context history
        historical_findings_summary = "No similar historical findings recalled."
        try:
            uuid_org = UUID(org_id)
            async with AsyncSessionLocal() as db:
                recall = ContextRecall(db)
                findings = await recall.recall_similar_findings(uuid_org, program_name, limit=5)
                if findings:
                    historical_findings_summary = json.dumps(findings)
        except Exception as e:
            logger.warning(f"Strategy planner failed context recall: {e}")

        # 2. Formulate Prompt directing CoT target prioritization
        prompt = (
            f"Autonomous Hunt Strategy Planning Request:\n"
            f"Program: {program_name}\n"
            f"Tech Stack: {tech_stack}\n"
            f"Endpoints to prioritize: {json.dumps(live_endpoints[:10])}\n"
            f"Historical context: {historical_findings_summary}\n\n"
            f"Design a strategic attack sequencing plan including:\n"
            f"1. High-value asset target priorities (Why?)\n"
            f"2. Custom exploitability vectors mapping to tech stack flaws\n"
            f"3. Boundary traversal directions (trust bypass targets)\n"
            f"4. Recommended scan schedule strategy (daily/weekly/realtime)"
        )

        response = await ai_orchestrator.generate_response(
            prompt=prompt,
            system_prompt=SystemPrompts.SCHEDULER,
            task_type="report",
            org_id=org_id
        )

        return {
            "org_id": org_id,
            "program": program_name,
            "strategic_plan": response,
            "source": "ai_strategy_planner"
        }

ai_strategy_planner = AIStrategyPlanner()
