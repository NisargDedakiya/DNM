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

export interface ExposureTimelineResponse {
  organization_id: string
  asset?: string | null
  snapshot: {
    id: string
    asset: string
    risk_score: number
    created_at: string
    state_size: number
  }
  drift: Record<string, any>
  risk_evolution: Record<string, any>
  risk_history: {
    organization_id: string
    asset?: string | null
    history: Array<{
      id: string
      asset: string
      previous_risk: number
      current_risk: number
      delta: number
      summary: string
      created_at: string
    }>
    average_risk: number
    latest_risk: number
    escalations: Array<Record<string, any>>
  }
  regressions: Record<string, any>
  summary: {
    total_exposures: number
    high_risk_exposures: number
    drift_severity: string
    risk_direction: string
    regression_count: number
  }
}

export interface ExposureDriftResponse {
  organization_id: string
  asset?: string | null
  drift_detected: boolean
  changes: Record<string, any>
  severity: string
  high_risk_changes: Array<Record<string, any>>
}

export interface RiskEvolutionResponse {
  organization_id: string
  asset?: string | null
  history: Array<{
    id: string
    organization_id: string
    asset: string
    previous_risk: number
    current_risk: number
    delta: number
    summary: string
    created_at: string
  }>
  average_risk: number
  latest_risk: number
  escalations: Array<Record<string, any>>
}

export interface ExposureRegressionResponse {
  organization_id: string
  asset?: string | null
  regressions: Array<Record<string, any>>
  repeat_exposures: Array<Record<string, any>>
  recurring_patterns: Array<Record<string, any>>
  regression_count: number
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
    asset?: string
    days?: number
    limit?: number
  }
) {
  const r = await api.get('/exposure/timeline', {
    params: { organization_id: organizationId, ...params },
  })
  return r.data as ExposureTimelineResponse
}

export async function getExposureDrift(
  organizationId: string,
  params?: {
    asset?: string
    limit?: number
  }
) {
  const r = await api.get('/exposure/drift', {
    params: { organization_id: organizationId, ...params },
  })
  return r.data as ExposureDriftResponse
}

export async function getRiskEvolution(
  organizationId: string,
  params?: {
    asset?: string
    limit?: number
  }
) {
  const r = await api.get('/exposure/risk-evolution', {
    params: { organization_id: organizationId, ...params },
  })
  return r.data as RiskEvolutionResponse
}

export async function getExposureRegressions(
  organizationId: string,
  params?: {
    asset?: string
    limit?: number
  }
) {
  const r = await api.get('/exposure/regressions', {
    params: { organization_id: organizationId, ...params },
  })
  return r.data as ExposureRegressionResponse
}
