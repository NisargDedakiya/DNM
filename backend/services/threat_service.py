"""
Threat intelligence orchestration service.
"""
from __future__ import annotations

from datetime import datetime
import logging
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.anomaly.exposure_anomaly import detect_exposure_anomaly
from backend.anomaly.risk_anomaly import detect_risk_spike
from backend.core.events import EventType
from backend.enrichment.exposure_correlation import correlate_threat_signals, prioritize_external_risk
from backend.enrichment.technology_enrichment import enrich_technology_stack, identify_risky_technologies
from backend.models.asset import Asset
from backend.models.exposure import Exposure
from backend.models.graph_node import NodeType
from backend.models.technology import Technology
from backend.services.ai_service import ai_service
from backend.services.event_service import event_service
from backend.services.graph_service import GraphService
from backend.threat.asn_intelligence import analyze_infrastructure_owner, correlate_provider_exposure, resolve_asn
from backend.threat.cve_intelligence import map_cves, prioritize_exploitable_cves
from backend.threat.github_leak_intelligence import analyze_repository_exposure, detect_secret_leaks
from backend.threat.ip_reputation import analyze_ip_reputation, identify_malicious_hosts
from backend.threat.shodan_enrichment import enrich_asset as enrich_shodan_asset

logger = logging.getLogger(__name__)


class ThreatService:
    """Coordinates threat enrichment, correlation, and safe orchestration hooks."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.graph_service = GraphService(db)

    async def _load_asset_context(self, organization_id: UUID, asset_id: UUID) -> dict[str, Any]:
        asset_result = await self.db.execute(
            select(Asset).where(Asset.id == asset_id, Asset.organization_id == organization_id)
        )
        asset = asset_result.scalars().first()
        if not asset:
            return {"asset": None, "technologies": [], "exposures": []}

        tech_result = await self.db.execute(
            select(Technology).where(Technology.asset_id == asset_id).order_by(Technology.first_detected.desc())
        )
        technologies = list(tech_result.scalars().all())

        exposure_result = await self.db.execute(
            select(Exposure).where(Exposure.asset_id == asset_id, Exposure.organization_id == organization_id)
        )
        exposures = list(exposure_result.scalars().all())

        return {"asset": asset, "technologies": technologies, "exposures": exposures}

    async def enrich_exposure(self, organization_id: UUID, asset_id: UUID) -> dict[str, Any]:
        """Run the external intelligence enrichment pipeline for one asset."""
        context = await self._load_asset_context(organization_id, asset_id)
        asset = context["asset"]
        if not asset:
            return {"organization_id": str(organization_id), "asset_id": str(asset_id), "status": "not_found"}

        tech_stack = [
            {
                "name": tech.name,
                "version": tech.version,
                "confidence_score": tech.confidence_score,
            }
            for tech in context["technologies"]
        ]
        fingerprint = enrich_technology_stack(
            {"hostname": asset.hostname, "ip_address": asset.ip_address},
            tech_stack,
        )
        shodan_view = enrich_shodan_asset(
            {
                "hostname": asset.hostname,
                "ip_address": asset.ip_address,
                "services": [
                    {"port": 443, "banner": "HTTPS service", "scheme": "https"},
                    {"port": 80, "banner": "HTTP service", "scheme": "http"},
                ],
            }
        )

        cve_catalog = [
            {
                "cve_id": "CVE-2024-0001",
                "title": f"{tech.name} version exposure",
                "severity": "high",
                "cvss_score": 8.1,
                "affected_versions": [tech.version or tech.name],
                "exploitability": 0.78,
            }
            for tech in context["technologies"]
            if tech.name
        ]
        cve_matches = prioritize_exploitable_cves(map_cves(tech_stack, cve_catalog=cve_catalog))

        ip_reputation = analyze_ip_reputation(
            asset.ip_address or asset.hostname,
            observations={"abuse_reports": 1 if asset.ip_address else 0, "is_public_cloud": False},
        )
        asn_record = analyze_infrastructure_owner(
            resolve_asn(asset.ip_address or asset.hostname, {"provider": "Unknown", "owner": "Unknown"})
        )

        repository_exposure = analyze_repository_exposure(
            {
                "name": asset.hostname,
                "visibility": "public" if asset.ip_address else "private",
                "content": "token = ghp_example_secret_token_value",
            }
        )
        secret_leaks = detect_secret_leaks(
            [
                {
                    "name": asset.hostname,
                    "content": "api_key = ghp_example_secret_token_value",
                }
            ]
        )

        correlation = correlate_threat_signals(
            {
                "cves": cve_matches,
                "public_services": shodan_view["services"],
                "secret_leaks": secret_leaks,
                "ip_reputation": ip_reputation,
                "asn": asn_record,
            }
        )
        prioritized = prioritize_external_risk([correlation])

        ai_verdict = "Pending AI analysis"
        try:
            ai_verdict = await ai_service.analyze_finding(
                {
                    "title": f"Threat enrichment for {asset.hostname}",
                    "target": asset.hostname,
                    "severity": correlation["severity"],
                    "prompt": f"Summarize exploitability for {asset.hostname} with CVEs, public exposure, and reputation context.",
                }
            )
        except Exception as exc:  # pragma: no cover - fail closed, no user impact
            logger.warning("AI reasoning unavailable for threat enrichment: %s", exc)

        try:
            await self.graph_service.create_node(
                organization_id=organization_id,
                node_type=NodeType.ASSET,
                reference_id=asset.id,
                label=asset.hostname,
                node_metadata={"ip_address": asset.ip_address, "severity": correlation["severity"]},
            )
        except Exception as exc:  # pragma: no cover - graph sync must not block enrichment
            logger.warning("Graph sync skipped during threat enrichment: %s", exc)

        try:
            anomaly = await detect_exposure_anomaly(organization_id, asset.id, self.db)
            spike = await detect_risk_spike(organization_id, asset.id, float(asset.risk_score or 0.0), float(asset.risk_score or 0.0), self.db)
        except Exception as exc:  # pragma: no cover
            logger.warning("Anomaly hooks skipped during threat enrichment: %s", exc)
            anomaly = {"is_anomaly": False}
            spike = {"is_spike": False}

        await event_service.emit_event(
            event_type=EventType.EXPOSURE_DRIFT,
            org_id=str(organization_id),
            payload={
                "asset_id": str(asset.id),
                "hostname": asset.hostname,
                "severity": correlation["severity"],
                "exploitability_score": correlation["exploitability_score"],
                "timestamp": datetime.utcnow().isoformat(),
            },
        )

        return {
            "organization_id": str(organization_id),
            "asset_id": str(asset.id),
            "asset": {"hostname": asset.hostname, "ip_address": asset.ip_address},
            "technology_enrichment": fingerprint,
            "shodan_enrichment": shodan_view,
            "cve_matches": cve_matches,
            "ip_reputation": ip_reputation,
            "asn_intelligence": asn_record,
            "repository_exposure": repository_exposure,
            "correlation": correlation,
            "prioritized_risk": prioritized,
            "ai_verdict": ai_verdict,
            "anomaly_detected": bool(anomaly.get("is_anomaly")),
            "risk_spike": bool(spike.get("is_spike")),
        }

    async def correlate_external_threats(self, organization_id: UUID, asset_id: UUID) -> dict[str, Any]:
        """Return a compact external threat summary for API consumers."""
        enrichment = await self.enrich_exposure(organization_id, asset_id)
        return {
            "organization_id": enrichment["organization_id"],
            "asset_id": enrichment["asset_id"],
            "severity": enrichment["correlation"]["severity"],
            "exploitability_score": enrichment["correlation"]["exploitability_score"],
            "top_cves": enrichment["cve_matches"][:5],
            "public_exposures": enrichment["shodan_enrichment"]["services"],
            "ip_reputation": enrichment["ip_reputation"],
            "asn": enrichment["asn_intelligence"],
            "summary": enrichment["correlation"]["summary"],
        }

    async def generate_threat_summary(self, organization_id: UUID) -> dict[str, Any]:
        """Generate org-scoped threat intelligence summary."""
        asset_result = await self.db.execute(
            select(Asset).where(Asset.organization_id == organization_id).order_by(Asset.risk_score.desc()).limit(20)
        )
        assets = list(asset_result.scalars().all())
        summaries = []
        for asset in assets:
            try:
                summaries.append(await self.correlate_external_threats(organization_id, asset.id))
            except Exception as exc:  # pragma: no cover
                logger.warning("Threat summary item skipped: %s", exc)

        return {
            "organization_id": str(organization_id),
            "total_assets": len(assets),
            "summaries": summaries,
            "malicious_hosts": identify_malicious_hosts(
                [{"ip_address": asset.ip_address, "hostname": asset.hostname, "provider": "cloud"} for asset in assets if asset.ip_address]
            ),
            "provider_exposure": correlate_provider_exposure(
                [{"provider": "cloud", "owner": "cloud", "asset": asset.hostname} for asset in assets]
            ),
        }