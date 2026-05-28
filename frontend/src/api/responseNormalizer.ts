export function normalizeFinding(raw: any) {
  return {
    id: raw.id || '',
    title: raw.title || 'Untitled Finding',
    description: raw.description || '',
    severity: (raw.severity || 'medium').toLowerCase(),
    status: (raw.status || 'open').toLowerCase(),
    asset_id: raw.asset_id || raw.asset?.id || null,
    organization_id: raw.organization_id || '',
    created_at: raw.created_at || new Date().toISOString(),
    updated_at: raw.updated_at || null,
    ...raw,
  }
}

export function normalizeFindingsList(rawList: any): any[] {
  if (!Array.isArray(rawList)) return []
  return rawList.map(normalizeFinding)
}

export function normalizeGraphData(raw: any) {
  const nodes = Array.isArray(raw.nodes)
    ? raw.nodes.map((n: any) => ({
        id: n.id || '',
        type: n.type || 'default',
        label: n.label || n.title || '',
        data: n.data || {},
        position: n.position || { x: 0, y: 0 },
        ...n,
      }))
    : []

  const edges = Array.isArray(raw.edges)
    ? raw.edges.map((e: any) => ({
        id: e.id || `${e.source}-${e.target}`,
        source: e.source || '',
        target: e.target || '',
        type: e.type || 'default',
        ...e,
      }))
    : []

  return { nodes, edges }
}
