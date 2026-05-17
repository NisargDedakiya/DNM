import api from '../client'

// ── Assets ───────────────────────────────────────────────
export interface Asset {
  id: string
  hostname: string
  ip_address?: string
  is_alive: boolean
  risk_score: number
  program_id: string
  organization_id?: string
  first_seen: string
  last_seen: string
}

export interface AssetPriority {
  asset_id: string
  hostname: string
  priority_score: number
  priority_level: 'critical' | 'high' | 'medium' | 'low' | 'info'
  recommended_recon_depth: string
  rank?: number
  score_breakdown: Record<string, number>
  factors: {
    risk_score: number
    active_exposures: number
    total_findings: number
    is_internet_facing: boolean
    asset_type: string
  }
}

export async function getAssets(params?: { program_id?: string; is_alive?: boolean }) {
  const r = await api.get('/assets/', { params })
  return r.data as Asset[]
}

export async function getHighValueAssets(organization_id: string, program_id?: string, min_priority = 'high') {
  const r = await api.get('/ai/high-value-assets', {
    params: { organization_id, program_id, min_priority },
  })
  return r.data
}

export async function getAssetPriorityTrend(asset_id: string) {
  const r = await api.get(`/assets/${asset_id}/priority-trend`)
  return r.data
}
