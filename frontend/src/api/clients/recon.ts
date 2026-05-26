import api from '../client'

// ── AI Recon Planning (Phase 18) ─────────────────────────
export interface ReconPlanRequest {
  organization_id: string
  program_id?: string
  program_name?: string
  scope_domains?: string[]
}

export interface WorkflowPreviewRequest {
  organization_id: string
  program_id?: string
  program_name?: string
  scope_domains?: string[]
  asset_types?: string[]
  risk_level?: string
  technologies?: string[]
  existing_coverage?: string[]
}

export async function generateReconPlan(req: ReconPlanRequest) {
  const r = await api.post('/ai/recon-plan', req)
  return r.data
}

export async function getRecommendations(organization_id: string, program_id?: string) {
  const r = await api.get('/ai/recommendations', { params: { organization_id, program_id } })
  return r.data
}

export async function getHighValueAssets(organization_id: string, program_id?: string, min_priority = 'high') {
  const r = await api.get('/ai/high-value-assets', { params: { organization_id, program_id, min_priority } })
  return r.data
}

export async function previewWorkflow(req: WorkflowPreviewRequest) {
  const r = await api.post('/ai/workflow-preview', req)
  return r.data
}

// ── Dashboard ─────────────────────────────────────────────
export async function getDashboardStats() {
  const r = await api.get('/dashboard/stats')
  return r.data
}

export async function getRecentActivity() {
  const r = await api.get('/dashboard/activity')
  return r.data
}
