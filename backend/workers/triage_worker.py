import logging
from typing import Dict, Any
from backend.services.event_service import event_service
from backend.services.notification_service import notification_service
from backend.core.events import EventType, SeverityLevel

logger = logging.getLogger(__name__)

class TriageWorker:
    """Consume findings and run AI triage."""

    async def run_ai_triage(self, finding_data: Dict[str, Any]) -> Dict[str, Any]:
        """Simulate AI triage and severity calculation."""
        # Here we would call the AI Copilot backend
        logger.info(f"Running AI triage on finding: {finding_data.get('title')}")
        
        # Mock logic
        return {
            "severity": SeverityLevel.CRITICAL if "SQL" in finding_data.get("title", "") else SeverityLevel.MEDIUM,
            "ai_confidence": 0.95
        }

    async def process_finding(self, org_id: str, finding_data: Dict[str, Any]):
        """Main workflow for processing a new finding."""
        logger.info(f"Processing new finding: {finding_data.get('finding_id')}")
        
        # 1. Execute AI triage
        triage_results = await self.run_ai_triage(finding_data)
        
        finding_data["severity"] = triage_results["severity"]
        finding_data["ai_confidence"] = triage_results["ai_confidence"]
        
        # 2. Publish Triaged Event
        await event_service.emit_finding_event(EventType.FINDING_TRIAGED, org_id, finding_data)
        
        # 3. Update DB (Mocked)
        # db.update_finding(...)
        
        # 4. Trigger Alerts
        if finding_data["severity"] in [SeverityLevel.CRITICAL, SeverityLevel.HIGH]:
            await event_service.emit_alert_event(org_id, finding_data)
            await notification_service.send_p1_alert(org_id, finding_data)

triage_worker = TriageWorker()
