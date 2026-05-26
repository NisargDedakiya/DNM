"""
Grid Service: Orchestrates autonomous monitoring grid, attack graph syncing, AI blast-radius, and anomaly checks.
"""
from __future__ import annotations

import logging
from datetime import datetime
from uuid import UUID

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.asset import Asset
from backend.models.exposure_mutation import ExposureMutation
from backend.models.anomaly_event import AnomalyEvent
from backend.models.grid_agent import GridAgent
from backend.services.event_service import event_service
from backend.services.exposure_service import ExposureService
from backend.services.graph_service import GraphService
from backend.services.ai_service import ai_service
from backend.services.investigation_service import InvestigationService
from backend.services.alert_service import AlertService
from backend.core.events import EventType
from backend.models.graph_node import NodeType
from backend.models.graph_edge import RelationshipType

from backend.autonomous.continuous_scheduler import schedule_monitoring_cycle, prioritize_monitoring_targets
from backend.anomaly.exposure_anomaly import detect_exposure_anomaly
from backend.anomaly.risk_anomaly import detect_risk_spike

logger = logging.getLogger(__name__)


class GridService:
    """
    Orchestrates continuous monitoring pipelines and executes autonomous exposure workflows.
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        self.exposure_service = ExposureService(db)
        self.graph_service = GraphService(db)
        self.investigation_service = InvestigationService(db)
        self.alert_service = AlertService(db)

    async def run_continuous_monitoring(self, organization_id: UUID) -> dict:
        """
        Orchestrate one cycle of target scans for the organization.

        Args:
            organization_id: Organization context

        Returns:
            dict: Monitoring cycle summary.
        """
        logger.info("[%s] Orchestrating grid continuous monitoring cycle", organization_id)
        
        # 1. Fetch prioritized targets
        targets = await prioritize_monitoring_targets(organization_id, self.db)
        
        # 2. Trigger scheduler cycle
        res = await schedule_monitoring_cycle(self.db)
        
        # Emit monitoring status update event
        await event_service.emit_event(
            event_type=EventType.MONITORING_HEALTH_UPDATED,
            org_id=str(organization_id),
            payload={
                "status": "healthy",
                "last_cycle": datetime.utcnow().isoformat(),
                "assets_checked": res.get("total_assets_monitored", 0),
                "mutations_found": res.get("total_mutations_triggered", 0),
            }
        )

        return res

    async def process_exposure_mutation(self, organization_id: UUID, mutation_id: UUID) -> dict:
        """
        Core autonomous exposure flow:
        - Recalculate risk evolution
        - Sync attack graph node & edges
        - Ask AI to evaluate blast radius
        - Trigger anomaly checks
        - Emit events to websocket clients
        - Optionally auto-create investigation

        Args:
            organization_id: Organization context
            mutation_id: UUID of detected exposure mutation

        Returns:
            dict: Outcome of autonomous processing pipeline.
        """
        logger.info("[%s] Processing exposure mutation: %s", organization_id, mutation_id)

        # 1. Fetch mutation
        stmt = select(ExposureMutation).where(
            and_(
                ExposureMutation.id == mutation_id,
                ExposureMutation.organization_id == organization_id,
            )
        )
        res = await self.db.execute(stmt)
        mutation = res.scalars().first()
        if not mutation:
            return {"status": "error", "message": "Mutation not found"}

        asset_data = mutation.asset
        asset_id = UUID(asset_data["id"]) if isinstance(asset_data.get("id"), str) else asset_data.get("id")

        # 2. Recalculate risk score evolution
        stmt_asset = select(Asset).where(Asset.id == asset_id)
        res_asset = await self.db.execute(stmt_asset)
        asset = res_asset.scalars().first()
        
        prev_score = asset.risk_score if asset else 0.0
        
        # Add risk increments based on severity
        added_risk = 1.5
        if mutation.severity == "critical":
            added_risk = 4.0
        elif mutation.severity == "high":
            added_risk = 3.0
        elif mutation.severity == "medium":
            added_risk = 1.8

        new_score = min(prev_score + added_risk, 10.0)
        
        if asset:
            asset.risk_score = new_score
            asset.last_seen = datetime.utcnow()
            await self.db.commit()

        # Check for risk spike
        spike_res = await detect_risk_spike(organization_id, asset_id, prev_score, new_score, self.db)

        # 3. Sync attack graph node and relationship
        graph_node = await self.graph_service.create_node(
            organization_id=organization_id,
            node_type=NodeType.EXPOSURE,
            reference_id=mutation.id,
            label=f"Mutation: {mutation.mutation_type}",
            node_metadata={
                "severity": mutation.severity,
                "mutation_type": mutation.mutation_type,
                "summary": mutation.summary,
            }
        )

        # Link asset to the mutation exposure node
        asset_node = await self.graph_service.get_node(
            organization_id=organization_id,
            node_type=NodeType.ASSET,
            reference_id=asset_id,
        )
        
        if asset_node:
            await self.graph_service.create_edge(
                organization_id=organization_id,
                source_node_id=asset_node.id,
                target_node_id=graph_node.id,
                relationship_type=RelationshipType.EXPOSES,
                confidence_score=0.9,
                notes=f"Detected mutation {mutation.mutation_type}",
            )

        # 4. Ask AI to evaluate blast radius
        ai_verdict = "Pending analysis"
        try:
            ai_prompt = (
                f"Analyze the blast radius of a mutation on asset {asset_data.get('hostname')} "
                f"({asset_data.get('ip_address')}). Mutation type: {mutation.mutation_type}, "
                f"Severity: {mutation.severity}. Summary: {mutation.summary}. Previous risk score: {prev_score}, "
                f"New risk score: {new_score}."
            )
            # Use ai_service to analyze the finding/mutation context
            ai_verdict = await ai_service.analyze_finding({
                "title": f"Mutation on {asset_data.get('hostname')}",
                "target": asset_data.get("hostname"),
                "severity": mutation.severity,
                "prompt": ai_prompt,
            })
        except Exception as exc:
            logger.error("AI reasoning failure: %s", exc)
            ai_verdict = "AI analysis failed due to system resource constraints."

        # 5. Run exposure anomaly detection
        anomaly_res = await detect_exposure_anomaly(organization_id, mutation.id, self.db)

        # 6. Publish WebSocket & Event-bus events
        # We broadcast the mutation detail to subscribers
        await event_service.emit_event(
            event_type=EventType.EXPOSURE_DRIFT,
            org_id=str(organization_id),
            payload={
                "mutation_id": str(mutation.id),
                "asset_id": str(asset_id),
                "hostname": asset_data.get("hostname"),
                "mutation_type": mutation.mutation_type,
                "severity": mutation.severity,
                "summary": mutation.summary,
                "ai_verdict": ai_verdict,
            }
        )

        # 7. Optionally auto-create investigation
        investigation_created = False
        investigation_details = {}
        
        if anomaly_res.get("is_anomaly") or spike_res.get("is_spike"):
            try:
                # Trigger a background AI-assisted investigation
                inv = await self.investigation_service.start_investigation(
                    organization_id=organization_id,
                    investigation_type="asset",
                    entity_id=asset_id,
                    analyst_note=f"Coordinated alert: {mutation.summary}",
                )
                investigation_created = True
                investigation_details = {
                    "investigation_id": inv.get("investigation_id"),
                    "ai_verdict": inv.get("ai_analysis", {}).get("verdict", "Coordinated anomaly"),
                }
            except Exception as exc:
                logger.error("Failed to auto-create investigation: %s", exc)

        return {
            "status": "success",
            "mutation_id": str(mutation.id),
            "risk_evolved": {
                "previous_score": prev_score,
                "new_score": new_score,
                "is_spike": spike_res.get("is_spike"),
            },
            "anomaly_detected": anomaly_res.get("is_anomaly"),
            "ai_blast_radius_verdict": ai_verdict,
            "investigation_auto_created": investigation_created,
            "investigation_details": investigation_details,
        }

    async def trigger_autonomous_response(self, organization_id: UUID, anomaly_id: UUID) -> dict:
        """
        Trigger defensive responses like creating alerts, sending notifications, and triaging vulnerabilities.

        Args:
            organization_id: Organization context
            anomaly_id: UUID of anomaly event

        Returns:
            dict: Response execution status.
        """
        logger.info("[%s] Triggering autonomous response for anomaly %s", organization_id, anomaly_id)
        
        # 1. Fetch anomaly
        stmt = select(AnomalyEvent).where(
            and_(
                AnomalyEvent.id == anomaly_id,
                AnomalyEvent.organization_id == organization_id,
            )
        )
        res = await self.db.execute(stmt)
        anomaly = res.scalars().first()
        
        if not anomaly:
            return {"status": "error", "message": "Anomaly not found"}

        # 2. Trigger high-signal alerting in AlertService
        alert = await self.alert_service.create_alert(
            organization_id=organization_id,
            program_id=organization_id,  # program/org matching
            alert_type="finding.p1_alert" if anomaly.severity in ("critical", "high") else "monitoring_alert",
            title=f"Autonomous Grid Alert: {anomaly.anomaly_type}",
            description=anomaly.summary,
            severity=anomaly.severity,
            delta_data={"anomaly_id": str(anomaly_id)},
        )

        return {
            "anomaly_id": str(anomaly_id),
            "response_status": "triggered",
            "alert_created": str(alert.id),
        }
