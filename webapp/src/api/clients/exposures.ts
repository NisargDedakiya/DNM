import api from '../client'

// ── Exposures ────────────────────────────────────────────
export interface Exposure {
  id: string
  asset_id: string
  organization_id: string
  finding_id?: string
  exposure_type: string
  risk_level: 'critical' | 'high' | 'medium' | 'low' | 'info'
  title: string
  description: string
  confidence_score: number
  risk_score: number
  first_detected: string
  last_detected: string
  detection_count: number
  is_active: boolean
  remediation_status?: string
  remediation_notes?: string
  evidence?: any
  fingerprint_data?: any
  categorization?: any
  recent_changes?: any[]
}

// List exposures for organization
export async function listExposures(
  organizationId: string,
  params?: {
    active_only?: boolean
    risk_level?: string
    exposure_type?: string
    limit?: number
  }
) {
  const r = await api.get('/exposures', {
    params: { organization_id: organizationId, ...params },
  })
  return r.data as Exposure[]
}

// Get exposure details
export async function getExposure(id: string) {
  const r = await api.get(`/exposures/${id}`)
  return r.data as Exposure
}

// Update exposure remediation status
export async function updateExposureStatus(
  id: string,
  data: {
    remediation_status?: string
    remediation_notes?: string
  }
) {
  const r = await api.patch(`/exposures/${id}`, data)
  return r.data as Exposure
}
