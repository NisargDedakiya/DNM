import api from '../client'

// ── Timeline ─────────────────────────────────────────────
export interface TimelineEvent {
  timestamp: string
  change_type: string
  change_reason?: string
  description: string
}

export interface AssetTimeline {
  asset: any
  timeline: TimelineEvent[]
  summary: Record<string, number>
  risk_trend: Array<{
    timestamp: string
    score: number
  }>
}

// Get asset timeline
export async function getAssetTimeline(
  assetId: string,
  organizationId: string,
  params?: {
    limit?: number
  }
) {
  const r = await api.get(`/timeline/assets/${assetId}`, {
    params: { organization_id: organizationId, ...params },
  })
  return r.data as AssetTimeline
}

// Get exposure timeline
export async function getExposureTimeline(
  organizationId: string,
  params?: {
    days?: number
    limit?: number
  }
) {
  const r = await api.get('/timeline/exposures', {
    params: { organization_id: organizationId, ...params },
  })
  return r.data
}
