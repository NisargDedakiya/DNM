"""
Relationship Service: builds and maintains the security graph topology.

This service is responsible for translating existing DB entities
(assets, exposures, findings, technologies, endpoints) into graph nodes
and edges.  It is the primary integration layer between the domain models
and the security intelligence graph.

Responsibilities
----------------
- map_asset_relationships()   → assets → endpoints, assets → technologies
- correlate_findings()        → findings → assets (affected_by edges)
- build_dependency_graph()    → technology dependency mapping
- associate_exposures()       → exposures → assets (exposes edges)

Security rules
--------------
- All operations scoped to organization_id.
- GraphService handles upsert safety and self-loop rejection.
- No domain-model rows are mutated by this service.
"""
from __future__ import annotations

import logging
from uuid import UUID

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.asset import Asset
from backend.models.endpoint import Endpoint
from backend.models.technology import Technology
from backend.models.exposure import Exposure
from backend.models.finding import Finding
from backend.models.graph_node import NodeType
from backend.models.graph_edge import RelationshipType
from backend.services.graph_service import GraphService

logger = logging.getLogger(__name__)


class RelationshipService:
    """
    Builds and synchronises the security graph topology from domain entities.
    """

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self._graph = GraphService(db)

    # =========================================================================
    # ASSET RELATIONSHIPS
    # =========================================================================

    async def map_asset_relationships(
        self,
        organization_id: UUID,
        program_id: UUID | None = None,
    ) -> dict[str, int]:
        """
        Ensure every asset, its endpoints, and technologies are in the graph,
        then wire the relationships:

        - asset --[hosts]--> endpoint
        - asset --[depends_on]--> technology

        Also groups assets sharing the same IP under a ``related_to`` edge.

        Returns
        -------
        dict with ``nodes_created`` and ``edges_created`` counts.
        """
        nodes_created = 0
        edges_created = 0

        # Fetch assets
        stmt = select(Asset).where(Asset.organization_id == organization_id)
        if program_id:
            stmt = stmt.where(Asset.program_id == program_id)
        result = await self.db.execute(stmt)
        assets = result.scalars().all()

        # Index: ip_address → list of asset nodes
        ip_to_asset_nodes: dict[str, list] = {}

        for asset in assets:
            # Create/upsert asset node
            asset_node = await self._graph.create_node(
                organization_id=organization_id,
                node_type=NodeType.ASSET,
                reference_id=asset.id,
                label=asset.hostname,
                node_metadata={
                    "ip_address": asset.ip_address,
                    "is_alive": asset.is_alive,
                    "risk_score": asset.risk_score,
                    "program_id": str(asset.program_id),
                },
            )
            nodes_created += 1

            # Track for IP-based correlation
            if asset.ip_address:
                ip_to_asset_nodes.setdefault(asset.ip_address, []).append(asset_node)

            # Fetch and wire endpoints
            ep_stmt = select(Endpoint).where(Endpoint.asset_id == asset.id)
            ep_result = await self.db.execute(ep_stmt)
            endpoints = ep_result.scalars().all()

            for ep in endpoints:
                ep_node = await self._graph.create_node(
                    organization_id=organization_id,
                    node_type=NodeType.ENDPOINT,
                    reference_id=ep.id,
                    label=f"{ep.method} {ep.path}",
                    node_metadata={
                        "path": ep.path,
                        "method": ep.method,
                        "status_code": ep.status_code,
                    },
                )
                nodes_created += 1
                edge = await self._graph.create_edge(
                    organization_id=organization_id,
                    source_node_id=asset_node.id,
                    target_node_id=ep_node.id,
                    relationship_type=RelationshipType.HOSTS,
                    confidence_score=1.0,
                )
                if edge:
                    edges_created += 1

            # Fetch and wire technologies
            tech_stmt = select(Technology).where(Technology.asset_id == asset.id)
            tech_result = await self.db.execute(tech_stmt)
            technologies = tech_result.scalars().all()

            for tech in technologies:
                tech_node = await self._graph.create_node(
                    organization_id=organization_id,
                    node_type=NodeType.TECHNOLOGY,
                    reference_id=tech.id,
                    label=f"{tech.name} {tech.version or ''}".strip(),
                    node_metadata={
                        "name": tech.name,
                        "version": tech.version,
                        "confidence_score": tech.confidence_score,
                    },
                )
                nodes_created += 1
                edge = await self._graph.create_edge(
                    organization_id=organization_id,
                    source_node_id=asset_node.id,
                    target_node_id=tech_node.id,
                    relationship_type=RelationshipType.DEPENDS_ON,
                    confidence_score=tech.confidence_score,
                )
                if edge:
                    edges_created += 1

        # Wire assets sharing the same IP as related_to each other
        for ip, asset_nodes in ip_to_asset_nodes.items():
            if len(asset_nodes) < 2:
                continue
            for i, src in enumerate(asset_nodes):
                for tgt in asset_nodes[i + 1:]:
                    edge = await self._graph.create_edge(
                        organization_id=organization_id,
                        source_node_id=src.id,
                        target_node_id=tgt.id,
                        relationship_type=RelationshipType.RELATED_TO,
                        confidence_score=0.9,
                        notes=f"Shared IP: {ip}",
                    )
                    if edge:
                        edges_created += 1

        logger.info(
            "Asset relationships mapped: org=%s nodes=%d edges=%d",
            organization_id, nodes_created, edges_created,
        )
        return {"nodes_created": nodes_created, "edges_created": edges_created}

    # =========================================================================
    # EXPOSURE ASSOCIATION
    # =========================================================================

    async def associate_exposures(
        self,
        organization_id: UUID,
    ) -> dict[str, int]:
        """
        Link all active exposures to their parent assets in the graph.

        asset --[exposes]--> exposure

        Confidence is derived from the exposure's confidence_score field.
        """
        nodes_created = 0
        edges_created = 0

        stmt = select(Exposure).where(
            and_(
                Exposure.organization_id == organization_id,
                Exposure.is_active == True,
            )
        )
        result = await self.db.execute(stmt)
        exposures = result.scalars().all()

        for exp in exposures:
            # Exposure node
            exp_node = await self._graph.create_node(
                organization_id=organization_id,
                node_type=NodeType.EXPOSURE,
                reference_id=exp.id,
                label=exp.title,
                node_metadata={
                    "exposure_type": exp.exposure_type,
                    "risk_level": exp.risk_level,
                    "risk_score": exp.risk_score,
                    "confidence_score": exp.confidence_score,
                    "remediation_status": exp.remediation_status,
                },
            )
            nodes_created += 1

            # Find parent asset node
            asset_node = await self._graph.get_node(
                organization_id=organization_id,
                node_type=NodeType.ASSET,
                reference_id=exp.asset_id,
            )
            if asset_node:
                edge = await self._graph.create_edge(
                    organization_id=organization_id,
                    source_node_id=asset_node.id,
                    target_node_id=exp_node.id,
                    relationship_type=RelationshipType.EXPOSES,
                    confidence_score=exp.confidence_score,
                    notes=f"risk={exp.risk_level} type={exp.exposure_type}",
                )
                if edge:
                    edges_created += 1

        logger.info(
            "Exposures associated: org=%s nodes=%d edges=%d",
            organization_id, nodes_created, edges_created,
        )
        return {"nodes_created": nodes_created, "edges_created": edges_created}

    # =========================================================================
    # FINDING CORRELATION
    # =========================================================================

    async def correlate_findings(
        self,
        organization_id: UUID,
    ) -> dict[str, int]:
        """
        Add finding nodes and wire them to affected assets.

        asset --[affected_by]--> finding

        Cross-finding correlation (shared endpoint, same title prefix) is
        captured as finding --[related_to]--> finding edges.
        """
        nodes_created = 0
        edges_created = 0

        stmt = select(Finding).where(Finding.organization_id == organization_id)
        result = await self.db.execute(stmt)
        findings = result.scalars().all()

        finding_nodes: list = []

        for finding in findings:
            f_node = await self._graph.create_node(
                organization_id=organization_id,
                node_type=NodeType.FINDING,
                reference_id=finding.id,
                label=finding.title,
                node_metadata={
                    "severity": finding.severity,
                    "status": finding.status,
                    "endpoint": finding.endpoint,
                    "program_id": str(finding.program_id),
                },
            )
            nodes_created += 1
            finding_nodes.append((finding, f_node))

            # Wire to asset if program/scan context gives us one
            # (findings in this schema link to program, not directly to asset;
            # we create the affected_by edge using endpoint-based matching)
            if finding.endpoint:
                # Look for an endpoint node matching the path
                ep_stmt = select(Endpoint).where(Endpoint.path == finding.endpoint)
                ep_res = await self.db.execute(ep_stmt)
                endpoints = ep_res.scalars().all()
                for ep in endpoints:
                    asset_node = await self._graph.get_node(
                        organization_id=organization_id,
                        node_type=NodeType.ASSET,
                        reference_id=ep.asset_id,
                    )
                    if asset_node:
                        edge = await self._graph.create_edge(
                            organization_id=organization_id,
                            source_node_id=asset_node.id,
                            target_node_id=f_node.id,
                            relationship_type=RelationshipType.AFFECTED_BY,
                            confidence_score=0.85,
                        )
                        if edge:
                            edges_created += 1

        # Cross-finding correlation: group by severity + first-word of title
        title_groups: dict[str, list] = {}
        for finding, f_node in finding_nodes:
            first_word = finding.title.split()[0].lower() if finding.title else "unknown"
            key = f"{finding.severity}::{first_word}"
            title_groups.setdefault(key, []).append(f_node)

        for group_nodes in title_groups.values():
            if len(group_nodes) < 2:
                continue
            for i, src in enumerate(group_nodes):
                for tgt in group_nodes[i + 1:]:
                    edge = await self._graph.create_edge(
                        organization_id=organization_id,
                        source_node_id=src.id,
                        target_node_id=tgt.id,
                        relationship_type=RelationshipType.RELATED_TO,
                        confidence_score=0.70,
                        notes="Correlated by severity + title prefix",
                    )
                    if edge:
                        edges_created += 1

        logger.info(
            "Findings correlated: org=%s nodes=%d edges=%d",
            organization_id, nodes_created, edges_created,
        )
        return {"nodes_created": nodes_created, "edges_created": edges_created}

    # =========================================================================
    # TECHNOLOGY DEPENDENCY GRAPH
    # =========================================================================

    async def build_dependency_graph(
        self,
        organization_id: UUID,
    ) -> dict[str, int]:
        """
        Build a technology dependency map by detecting shared-stack patterns.

        Technologies with the same name detected on multiple assets are
        wired as related_to each other, enabling "blast radius" analysis
        (e.g. all assets running Apache 2.4.49 are correlated).
        """
        edges_created = 0

        # Fetch all technology nodes for the org
        tech_nodes = await self._graph.list_nodes(
            organization_id=organization_id,
            node_type=NodeType.TECHNOLOGY,
            limit=2000,
        )

        # Group by technology name (normalised)
        name_groups: dict[str, list] = {}
        for node in tech_nodes:
            meta = node.node_metadata or {}
            name_key = (meta.get("name") or "").lower().strip()
            if not name_key:
                continue
            name_groups.setdefault(name_key, []).append(node)

        # Wire same-name technology nodes across different assets
        for tech_name, nodes_in_group in name_groups.items():
            if len(nodes_in_group) < 2:
                continue
            for i, src in enumerate(nodes_in_group):
                for tgt in nodes_in_group[i + 1:]:
                    edge = await self._graph.create_edge(
                        organization_id=organization_id,
                        source_node_id=src.id,
                        target_node_id=tgt.id,
                        relationship_type=RelationshipType.RELATED_TO,
                        confidence_score=0.80,
                        notes=f"Shared technology: {tech_name}",
                    )
                    if edge:
                        edges_created += 1

        logger.info(
            "Dependency graph built: org=%s edges_created=%d",
            organization_id, edges_created,
        )
        return {"edges_created": edges_created}

    # =========================================================================
    # FULL GRAPH BOOTSTRAP
    # =========================================================================

    async def bootstrap_full_graph(
        self,
        organization_id: UUID,
        program_id: UUID | None = None,
    ) -> dict[str, int]:
        """
        Run all four relationship-building operations in sequence.

        Intended for first-time graph population or periodic full refresh.
        Returns aggregated node/edge creation counts.
        """
        totals: dict[str, int] = {"nodes_created": 0, "edges_created": 0}

        for fn in [
            lambda: self.map_asset_relationships(organization_id, program_id),
            lambda: self.associate_exposures(organization_id),
            lambda: self.correlate_findings(organization_id),
            lambda: self.build_dependency_graph(organization_id),
        ]:
            result = await fn()
            totals["nodes_created"] += result.get("nodes_created", 0)
            totals["edges_created"] += result.get("edges_created", 0)

        logger.info(
            "Full graph bootstrap: org=%s total_nodes=%d total_edges=%d",
            organization_id, totals["nodes_created"], totals["edges_created"],
        )
        return totals
