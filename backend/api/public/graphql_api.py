"""
GraphQL-style public API for nested intelligence queries.
"""
from __future__ import annotations

from collections import defaultdict
from uuid import UUID

from fastapi import APIRouter, Depends, Header
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database.session import get_db
from backend.models.attack_path import AttackPath
from backend.models.blast_radius_event import BlastRadiusEvent
from backend.models.exposure_event import ExposureEvent
from backend.models.finding import Finding
from backend.models.monitoring_rule import MonitoringRule
from backend.models.threat_intel import ThreatIntel
from backend.services.developer_service import DeveloperService

router = APIRouter(prefix="/public", tags=["public-graphql"])

GRAPHQL_SCHEMA = """
type Query {
  findings(organizationId: ID!, page: Int, pageSize: Int): [Finding]
  attackPaths(organizationId: ID!, depth: Int): [AttackPath]
  blastRadius(organizationId: ID!): [BlastRadius]
  exposureIntel(organizationId: ID!): [ExposureIntel]
  monitoringStatus(organizationId: ID!): MonitoringStatus
}
""".strip()


class GraphQLRequest(BaseModel):
    query: str
    variables: dict = Field(default_factory=dict)
    organization_id: UUID


async def get_developer_service(db: AsyncSession = Depends(get_db)) -> DeveloperService:
    return DeveloperService(db)


async def _authorize(
    organization_id: UUID,
    api_key: str = Header(..., alias="X-API-Key"),
    service: DeveloperService = Depends(get_developer_service),
) -> dict:
    return await service.validate_developer_request(
        organization_id=organization_id,
        api_key_secret=api_key,
        endpoint="graphql",
    )


def _normalize_query(query: str) -> str:
    return query.lower().replace(" ", "").replace("\n", "")


async def _build_attack_graph(db: AsyncSession, organization_id: UUID, depth: int = 2) -> dict:
    result = await db.execute(
        select(AttackPath).where(AttackPath.organization_id == organization_id),
    )
    paths = result.scalars().all()
    nodes: dict[str, dict] = {}
    edges: list[dict] = []

    for path in paths:
        nodes.setdefault(path.source_asset, {"id": path.source_asset, "type": "asset"})
        nodes.setdefault(path.target_asset, {"id": path.target_asset, "type": "asset"})
        edges.append(
            {
                "source": path.source_asset,
                "target": path.target_asset,
                "severity": path.severity,
                "exploitability_score": path.exploitability_score,
            },
        )

    adjacency = defaultdict(list)
    for edge in edges:
        adjacency[edge["source"]].append(edge)

    def walk(node_id: str, current_depth: int) -> dict:
        if current_depth >= depth:
            return {"id": node_id, "children": []}
        children = [
            {"edge": edge, "node": walk(edge["target"], current_depth + 1)}
            for edge in adjacency.get(node_id, [])
        ]
        return {"id": node_id, "children": children}

    roots = [walk(node_id, 0) for node_id in nodes.keys()]
    return {"nodes": list(nodes.values()), "edges": edges, "traversal": roots}


async def execute_graphql_query(
    db: AsyncSession,
    organization_id: UUID,
    query: str,
    variables: dict | None = None,
) -> dict:
    normalized = _normalize_query(query)
    variables = variables or {}
    response: dict[str, object] = {}

    if "findings" in normalized:
        page = int(variables.get("page", 1))
        page_size = int(variables.get("pageSize", 20))
        query_stmt = (
            select(Finding)
            .where(Finding.organization_id == organization_id)
            .order_by(Finding.created_at.desc())
            .offset(max(page - 1, 0) * min(max(page_size, 1), 100))
            .limit(min(max(page_size, 1), 100))
        )
        result = await db.execute(query_stmt)
        rows = result.scalars().all()
        response["findings"] = [
            {
                "id": row.id,
                "title": row.title,
                "severity": row.severity.value if hasattr(row.severity, "value") else str(row.severity),
                "status": row.status.value if hasattr(row.status, "value") else str(row.status),
                "endpoint": row.endpoint,
                "created_at": row.created_at,
            }
            for row in rows
        ]

    if "attackpaths" in normalized:
        depth = int(variables.get("depth", 2))
        response["attackPaths"] = await _build_attack_graph(db, organization_id, depth=depth)

    if "blastradius" in normalized:
        blast_rows = await db.execute(
            select(BlastRadiusEvent).where(BlastRadiusEvent.organization_id == organization_id).order_by(BlastRadiusEvent.created_at.desc()),
        )
        response["blastRadius"] = [
            {
                "id": row.id,
                "impact_score": row.impact_score,
                "summary": row.summary,
                "affected_assets": row.affected_assets or [],
                "created_at": row.created_at,
            }
            for row in blast_rows.scalars().all()
        ]

    if "exposureintel" in normalized:
        exposures = await db.execute(
            select(ExposureEvent).where(ExposureEvent.organization_id == organization_id).order_by(ExposureEvent.created_at.desc()),
        )
        intel = await db.execute(
            select(ThreatIntel).where(ThreatIntel.organization_id == organization_id).order_by(ThreatIntel.created_at.desc()),
        )
        response["exposureIntel"] = {
            "exposures": [
                {
                    "id": item.id,
                    "asset": item.asset,
                    "event_type": item.event_type,
                    "severity": item.severity,
                    "created_at": item.created_at,
                }
                for item in exposures.scalars().all()
            ],
            "threat_intelligence": [
                {
                    "id": item.id,
                    "asset": item.asset,
                    "intelligence_type": item.intelligence_type,
                    "severity": item.severity,
                    "summary": item.summary,
                    "created_at": item.created_at,
                }
                for item in intel.scalars().all()
            ],
        }

    if "monitoringstatus" in normalized:
        rules = await db.execute(
            select(MonitoringRule).where(MonitoringRule.organization_id == organization_id).order_by(MonitoringRule.created_at.desc()),
        )
        rows = rules.scalars().all()
        response["monitoringStatus"] = {
            "total_rules": len(rows),
            "enabled_rules": sum(1 for row in rows if row.enabled),
            "active_rules": sum(1 for row in rows if getattr(row, "is_active", True)),
        }

    return {"data": response, "schema": GRAPHQL_SCHEMA}


@router.post("/graphql")
async def graphql_endpoint(
    request: GraphQLRequest,
    api_key: str = Header(..., alias="X-API-Key"),
    db: AsyncSession = Depends(get_db),
    service: DeveloperService = Depends(get_developer_service),
) -> dict:
    await service.validate_developer_request(
        organization_id=request.organization_id,
        api_key_secret=api_key,
        endpoint="graphql",
    )
    return await execute_graphql_query(db, request.organization_id, request.query, request.variables)
