import api from '../client'

// ── Graph/Topology ──────────────────────────────────────
export interface GraphNode {
  id: string
  node_type: string
  reference_id: string
  label: string
  metadata?: any
}

export interface GraphEdge {
  source: string
  target: string
  relationship_type: string
  metadata?: any
}

export interface AssetGraph {
  center: GraphNode
  nodes: GraphNode[]
  edges: GraphEdge[]
}

// Get asset node neighbourhood
export async function getAssetGraph(
  assetId: string,
  organizationId: string,
  params?: {
    direction?: 'outgoing' | 'incoming' | 'both'
    relationship_types?: string[]
    limit?: number
  }
) {
  const r = await api.get(`/graph/assets/${assetId}`, {
    params: { organization_id: organizationId, ...params },
  })
  return r.data as AssetGraph
}

// Get exposure graph
export async function getExposureGraph(
  organizationId: string,
  params?: {
    limit?: number
    offset?: number
  }
) {
  const r = await api.get('/graph/exposures', {
    params: { organization_id: organizationId, ...params },
  })
  return r.data
}

// Bootstrap/refresh full graph
export async function bootstrapGraph(organizationId: string) {
  const r = await api.post('/graph/bootstrap', { organization_id: organizationId })
  return r.data
}
