"""
Graph API routes: security intelligence graph endpoints.

All routes:
- Require JWT authentication via get_current_user.
- Enforce workspace isolation via RBAC validate_workspace_access.
- Use async FastAPI patterns consistent with the rest of the codebase.
- Are primarily read-only (GET); write operations require RUN_SCANS permission.

Route map
---------
GET  /graph/assets/{asset_id}        → asset node + neighbours
GET  /graph/exposures                → exposure node listing with edges
GET  /graph/findings                 → finding node listing with correlations
GET  /graph/intelligence-map         → full graph for UI visualisation
GET  /graph/traverse/{node_id}       → bounded BFS traversal from any node
GET  /graph/risk-propagation/{id}    → risk propagation from a seed node
GET  /graph/clusters                 → high-risk cluster identification
GET  /graph/stats                    → graph statistics summary
POST /graph/bootstrap                → build/refresh the full graph topology
POST /graph/nodes                    → manually create a graph node
POST /graph/edges                    → manually create a graph edge
"""
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.auth.dependencies import get_current_user
from backend.database.session import get_db
from backend.models.user import User
from backend.core.permissions import Permission, RBACService
from backend.services.graph_service import GraphService
from backend.services.relationship_service import RelationshipService
from backend.services.intelligence_graph_service import IntelligenceGraphService
from backend.models.graph_node import NodeType
from backend.models.graph_edge import RelationshipType

router = APIRouter(prefix="/graph", tags=["graph"])


# ── Dependency helpers ────────────────────────────────────────────────────────

async def get_rbac(db: AsyncSession = Depends(get_db)) -> RBACService:
    return RBACService(db)


async def get_graph_service(db: AsyncSession = Depends(get_db)) -> GraphService:
    return GraphService(db)


async def get_relationship_service(db: AsyncSession = Depends(get_db)) -> RelationshipService:
    return RelationshipService(db)


async def get_intelligence_service(db: AsyncSession = Depends(get_db)) -> IntelligenceGraphService:
    return IntelligenceGraphService(db)


# ── Workspace enforcement helper ───────────────────────────────────────────────

async def _require_workspace(user_id: UUID, org_id: UUID, rbac: RBACService) -> None:
    await rbac.validate_workspace_access(user_id, org_id)


# =============================================================================
# ASSET GRAPH
# =============================================================================

@router.get(
    "/assets/{asset_id}",
    summary="Asset node neighbourhood",
    description=(
        "Returns the graph node for a specific asset and its one-hop "
        "neighbours (endpoints, exposures, technologies, findings). "
        "Workspace isolation enforced via organization_id."
    ),
)
async def get_asset_graph(
    asset_id: UUID,
    organization_id: UUID = Query(..., description="Organisation workspace ID"),
    direction: str = Query("outgoing", description="outgoing | incoming | both"),
    relationship_types: list[str] | None = Query(None, description="Filter edge types"),
    limit: int = Query(50, ge=1, le=200),
    current_user: User = Depends(get_current_user),
    graph_svc: GraphService = Depends(get_graph_service),
    rbac: RBACService = Depends(get_rbac),
) -> dict[str, Any]:
    """
    One-hop neighbourhood of an asset node.

    **Requires**: VIEW_ASSETS permission.

    Returns
    -------
    JSON with ``center`` (the asset node), ``edges``, and ``nodes`` (neighbours).
    """
    await _require_workspace(current_user.id, organization_id, rbac)
    await rbac.check_permission(current_user.id, organization_id, Permission.VIEW_ASSETS)

    # Resolve the graph node for this asset reference_id
    node = await graph_svc.get_node(
        organization_id=organization_id,
        node_type=NodeType.ASSET,
        reference_id=asset_id,
    )
    if node is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Graph node not found for this asset. Run /graph/bootstrap first.",
        )

    return await graph_svc.get_connected_nodes(
        organization_id=organization_id,
        node_id=node.id,
        direction=direction,
        relationship_types=relationship_types,
        limit=limit,
    )


# =============================================================================
# EXPOSURE GRAPH
# =============================================================================

@router.get(
    "/exposures",
    summary="Exposure node graph view",
    description=(
        "Returns all exposure graph nodes for an organisation with their "
        "connecting edges to assets and findings."
    ),
)
async def get_exposure_graph(
    organization_id: UUID = Query(..., description="Organisation workspace ID"),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    graph_svc: GraphService = Depends(get_graph_service),
    rbac: RBACService = Depends(get_rbac),
) -> dict[str, Any]:
    """
    List exposure nodes with their graph edges.

    **Requires**: VIEW_FINDINGS permission.
    """
    await _require_workspace(current_user.id, organization_id, rbac)
    await rbac.check_permission(current_user.id, organization_id, Permission.VIEW_FINDINGS)

    nodes = await graph_svc.list_nodes(
        organization_id=organization_id,
        node_type=NodeType.EXPOSURE,
        limit=limit,
        offset=offset,
    )

    result = []
    for node in nodes:
        neighbours = await graph_svc.get_connected_nodes(
            organization_id=organization_id,
            node_id=node.id,
            direction="incoming",  # asset → exposure
            limit=10,
        )
        result.append({
            "node": {
                "id": str(node.id),
                "label": node.label,
                "metadata": node.node_metadata,
                "created_at": node.created_at.isoformat() if node.created_at else None,
            },
            "connected_assets": neighbours["nodes"],
            "edge_count": len(neighbours["edges"]),
        })

    return {
        "exposures": result,
        "total": len(result),
        "limit": limit,
        "offset": offset,
    }


# =============================================================================
# FINDINGS GRAPH
# =============================================================================

@router.get(
    "/findings",
    summary="Finding correlation graph",
    description=(
        "Returns finding nodes with their correlation edges (related_to) "
        "and affected asset edges."
    ),
)
async def get_findings_graph(
    organization_id: UUID = Query(..., description="Organisation workspace ID"),
    severity: str | None = Query(None, description="Filter by severity: critical, high, medium, low, info"),
    limit: int = Query(100, ge=1, le=500),
    current_user: User = Depends(get_current_user),
    graph_svc: GraphService = Depends(get_graph_service),
    rbac: RBACService = Depends(get_rbac),
) -> dict[str, Any]:
    """
    Finding nodes with correlation and affected-asset relationships.

    **Requires**: VIEW_FINDINGS permission.
    """
    await _require_workspace(current_user.id, organization_id, rbac)
    await rbac.check_permission(current_user.id, organization_id, Permission.VIEW_FINDINGS)

    nodes = await graph_svc.list_nodes(
        organization_id=organization_id,
        node_type=NodeType.FINDING,
        limit=limit,
    )

    # Filter by severity if requested
    if severity:
        nodes = [
            n for n in nodes
            if (n.node_metadata or {}).get("severity") == severity
        ]

    result = []
    for node in nodes:
        neighbours = await graph_svc.get_connected_nodes(
            organization_id=organization_id,
            node_id=node.id,
            direction="both",
            relationship_types=["related_to", "affected_by"],
            limit=20,
        )
        result.append({
            "node": {
                "id": str(node.id),
                "label": node.label,
                "metadata": node.node_metadata,
            },
            "correlations": [
                n for n in neighbours["nodes"]
                if any(
                    e["relationship_type"] == "related_to"
                    for e in neighbours["edges"]
                    if e["source_node_id"] == str(node.id) or e["target_node_id"] == str(node.id)
                )
            ],
            "affected_assets": [
                n for n in neighbours["nodes"]
                if n.get("node_type") == NodeType.ASSET.value
            ],
        })

    return {"findings": result, "total": len(result)}


# =============================================================================
# INTELLIGENCE MAP
# =============================================================================

@router.get(
    "/intelligence-map",
    summary="Full security intelligence graph map",
    description=(
        "Returns the complete security intelligence graph for the organisation: "
        "all nodes, edges, risk clusters, and surface analysis. "
        "Designed for graph visualisation libraries (D3, Cytoscape, vis.js)."
    ),
)
async def get_intelligence_map(
    organization_id: UUID = Query(..., description="Organisation workspace ID"),
    program_id: UUID | None = Query(None, description="Optional program scope"),
    current_user: User = Depends(get_current_user),
    intel_svc: IntelligenceGraphService = Depends(get_intelligence_service),
    rbac: RBACService = Depends(get_rbac),
) -> dict[str, Any]:
    """
    Full intelligence map for graph visualisation.

    **Requires**: VIEW_ASSETS permission.

    Returns
    -------
    JSON with ``nodes``, ``edges``, ``stats``, ``risk_summary``, and ``surface_analysis``.
    """
    await _require_workspace(current_user.id, organization_id, rbac)
    await rbac.check_permission(current_user.id, organization_id, Permission.VIEW_ASSETS)

    return await intel_svc.build_intelligence_map(
        organization_id=organization_id,
        program_id=program_id,
    )


# =============================================================================
# BOUNDED TRAVERSAL
# =============================================================================

@router.get(
    "/traverse/{node_id}",
    summary="Bounded BFS graph traversal",
    description=(
        "Performs a bounded breadth-first traversal from the given node. "
        "Depth is capped at 5 hops maximum."
    ),
)
async def traverse_from_node(
    node_id: UUID,
    organization_id: UUID = Query(..., description="Organisation workspace ID"),
    max_depth: int = Query(3, ge=1, le=5, description="Max traversal depth (hard cap: 5)"),
    direction: str = Query("outgoing", description="outgoing | incoming | both"),
    relationship_types: list[str] | None = Query(None, description="Edge type whitelist"),
    current_user: User = Depends(get_current_user),
    graph_svc: GraphService = Depends(get_graph_service),
    rbac: RBACService = Depends(get_rbac),
) -> dict[str, Any]:
    """
    BFS traversal from any graph node.

    **Requires**: VIEW_ASSETS permission.

    Returns
    -------
    JSON with ``nodes`` dict, ``edges`` list, ``depth``, and counts.
    """
    await _require_workspace(current_user.id, organization_id, rbac)
    await rbac.check_permission(current_user.id, organization_id, Permission.VIEW_ASSETS)

    # Verify node belongs to this org
    node = await graph_svc.get_node_by_id(organization_id, node_id)
    if node is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Node not found or access denied",
        )

    return await graph_svc.traverse_graph(
        organization_id=organization_id,
        start_node_id=node_id,
        max_depth=max_depth,
        relationship_types=relationship_types,
        direction=direction,
    )


# =============================================================================
# RISK PROPAGATION
# =============================================================================

@router.get(
    "/risk-propagation/{node_id}",
    summary="Risk propagation from seed node",
    description=(
        "Calculates how risk from a high-risk node propagates through the graph "
        "via weighted edges. Returns affected nodes with propagated risk scores."
    ),
)
async def get_risk_propagation(
    node_id: UUID,
    organization_id: UUID = Query(..., description="Organisation workspace ID"),
    max_depth: int = Query(3, ge=1, le=5),
    current_user: User = Depends(get_current_user),
    intel_svc: IntelligenceGraphService = Depends(get_intelligence_service),
    graph_svc: GraphService = Depends(get_graph_service),
    rbac: RBACService = Depends(get_rbac),
) -> dict[str, Any]:
    """
    Risk propagation analysis from a seed node.

    **Requires**: VIEW_FINDINGS permission.
    """
    await _require_workspace(current_user.id, organization_id, rbac)
    await rbac.check_permission(current_user.id, organization_id, Permission.VIEW_FINDINGS)

    node = await graph_svc.get_node_by_id(organization_id, node_id)
    if node is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Node not found or access denied",
        )

    return await intel_svc.calculate_risk_propagation(
        organization_id=organization_id,
        start_node_id=node_id,
        max_depth=max_depth,
    )


# =============================================================================
# HIGH-RISK CLUSTERS
# =============================================================================

@router.get(
    "/clusters",
    summary="High-risk node clusters",
    description=(
        "Identifies clusters of densely-interconnected high-risk nodes "
        "in the security graph. Useful for blast-radius analysis."
    ),
)
async def get_risk_clusters(
    organization_id: UUID = Query(..., description="Organisation workspace ID"),
    risk_threshold: float = Query(0.6, ge=0.0, le=1.0, description="Minimum risk_score to seed a cluster"),
    min_cluster_size: int = Query(2, ge=2, le=50, description="Minimum nodes per cluster"),
    current_user: User = Depends(get_current_user),
    intel_svc: IntelligenceGraphService = Depends(get_intelligence_service),
    rbac: RBACService = Depends(get_rbac),
) -> dict[str, Any]:
    """
    High-risk cluster identification.

    **Requires**: VIEW_FINDINGS permission.
    """
    await _require_workspace(current_user.id, organization_id, rbac)
    await rbac.check_permission(current_user.id, organization_id, Permission.VIEW_FINDINGS)

    return await intel_svc.identify_high_risk_clusters(
        organization_id=organization_id,
        risk_threshold=risk_threshold,
        min_cluster_size=min_cluster_size,
    )


# =============================================================================
# GRAPH STATS
# =============================================================================

@router.get(
    "/stats",
    summary="Graph statistics summary",
    description="Returns aggregate node/edge counts broken down by type.",
)
async def get_graph_stats(
    organization_id: UUID = Query(..., description="Organisation workspace ID"),
    current_user: User = Depends(get_current_user),
    graph_svc: GraphService = Depends(get_graph_service),
    rbac: RBACService = Depends(get_rbac),
) -> dict[str, Any]:
    """
    Graph statistics for dashboard widgets.

    **Requires**: VIEW_ASSETS permission.
    """
    await _require_workspace(current_user.id, organization_id, rbac)
    await rbac.check_permission(current_user.id, organization_id, Permission.VIEW_ASSETS)

    return await graph_svc.get_graph_stats(organization_id)


# =============================================================================
# GRAPH BOOTSTRAP
# =============================================================================

@router.post(
    "/bootstrap",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Bootstrap / refresh the intelligence graph",
    description=(
        "Builds or refreshes the full intelligence graph by reading all existing "
        "entities and wiring nodes and edges. Safe to run multiple times (idempotent). "
        "Requires RUN_SCANS permission."
    ),
)
async def bootstrap_graph(
    organization_id: UUID = Query(..., description="Organisation workspace ID"),
    program_id: UUID | None = Query(None, description="Optional program scope"),
    current_user: User = Depends(get_current_user),
    rel_svc: RelationshipService = Depends(get_relationship_service),
    rbac: RBACService = Depends(get_rbac),
) -> dict[str, Any]:
    """
    Build or refresh the full security intelligence graph.

    **Requires**: RUN_SCANS permission (analyst+).

    Returns
    -------
    JSON with ``nodes_created`` and ``edges_created`` totals.
    """
    await _require_workspace(current_user.id, organization_id, rbac)
    await rbac.check_permission(current_user.id, organization_id, Permission.RUN_SCANS)

    try:
        result = await rel_svc.bootstrap_full_graph(
            organization_id=organization_id,
            program_id=program_id,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Graph bootstrap failed: {exc}",
        ) from exc

    return {
        "status": "bootstrapped",
        "organization_id": str(organization_id),
        "program_id": str(program_id) if program_id else None,
        **result,
    }


# =============================================================================
# MANUAL NODE CREATION
# =============================================================================

@router.post(
    "/nodes",
    status_code=status.HTTP_201_CREATED,
    summary="Manually create a graph node",
    description="Create a graph node for an entity that hasn't been auto-indexed.",
)
async def create_graph_node(
    organization_id: UUID = Query(..., description="Organisation workspace ID"),
    node_type: str = Query(..., description="Node type: asset, endpoint, technology, exposure, finding, scan"),
    reference_id: UUID = Query(..., description="UUID of the source entity"),
    label: str | None = Query(None, description="Display label"),
    current_user: User = Depends(get_current_user),
    graph_svc: GraphService = Depends(get_graph_service),
    rbac: RBACService = Depends(get_rbac),
) -> dict[str, Any]:
    """
    Manually add a node to the graph.

    **Requires**: RUN_SCANS permission.
    """
    await _require_workspace(current_user.id, organization_id, rbac)
    await rbac.check_permission(current_user.id, organization_id, Permission.RUN_SCANS)

    try:
        nt = NodeType(node_type)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid node_type '{node_type}'. Valid: {[t.value for t in NodeType]}",
        )

    node = await graph_svc.create_node(
        organization_id=organization_id,
        node_type=nt,
        reference_id=reference_id,
        label=label,
    )
    return {
        "id": str(node.id),
        "node_type": node.node_type,
        "reference_id": str(node.reference_id),
        "label": node.label,
        "created_at": node.created_at.isoformat() if node.created_at else None,
    }


# =============================================================================
# MANUAL EDGE CREATION
# =============================================================================

@router.post(
    "/edges",
    status_code=status.HTTP_201_CREATED,
    summary="Manually create a graph edge",
    description="Create a directed edge between two existing graph nodes.",
)
async def create_graph_edge(
    organization_id: UUID = Query(..., description="Organisation workspace ID"),
    source_node_id: UUID = Query(..., description="Source graph node ID"),
    target_node_id: UUID = Query(..., description="Target graph node ID"),
    relationship_type: str = Query(..., description="Relationship type: hosts, exposes, depends_on, related_to, discovered_by, affected_by"),
    confidence_score: float = Query(1.0, ge=0.0, le=1.0),
    notes: str | None = Query(None),
    current_user: User = Depends(get_current_user),
    graph_svc: GraphService = Depends(get_graph_service),
    rbac: RBACService = Depends(get_rbac),
) -> dict[str, Any]:
    """
    Manually add a directed edge to the graph.

    **Requires**: RUN_SCANS permission.
    """
    await _require_workspace(current_user.id, organization_id, rbac)
    await rbac.check_permission(current_user.id, organization_id, Permission.RUN_SCANS)

    try:
        rt = RelationshipType(relationship_type)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid relationship_type '{relationship_type}'. Valid: {[r.value for r in RelationshipType]}",
        )

    if source_node_id == target_node_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Self-loop edges are not allowed (source_node_id == target_node_id).",
        )

    edge = await graph_svc.create_edge(
        organization_id=organization_id,
        source_node_id=source_node_id,
        target_node_id=target_node_id,
        relationship_type=rt,
        confidence_score=confidence_score,
        notes=notes,
    )
    if edge is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Edge creation rejected (self-loop guard triggered).",
        )

    return {
        "id": str(edge.id),
        "source_node_id": str(edge.source_node_id),
        "target_node_id": str(edge.target_node_id),
        "relationship_type": edge.relationship_type,
        "confidence_score": edge.confidence_score,
        "weight": edge.weight,
        "created_at": edge.created_at.isoformat() if edge.created_at else None,
    }
