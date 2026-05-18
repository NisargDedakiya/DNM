import api from '../client'

// ── Copilot / AI ───────────────────────────────────────
export interface TriageRequest {
  finding_id: string
}

export interface TriageResult {
  finding_id: string
  severity: string
  confidence: number
  recommendation: string
  justification: string
}

export interface ReportRequest {
  finding_ids: string[]
  report_type?: 'executive' | 'technical' | 'summary'
}

export interface ReconPlanRequest {
  target: string
  scope?: string
  objectives?: string[]
}

export interface ReconPlan {
  id: string
  target: string
  stages: ReconStage[]
  estimated_duration: string
}

export interface ReconStage {
  name: string
  tools: string[]
  description: string
}

export async function triageFinding(request: TriageRequest) {
  const r = await api.post('/ai/triage', request)
  return r.data as TriageResult
}

export async function generateReport(request: ReportRequest) {
  const r = await api.post('/ai/report', request)
  return r.data
}

export async function planRecon(request: ReconPlanRequest) {
  const r = await api.post('/ai/recon-plan', request)
  return r.data as ReconPlan
}

export async function getRecommendations(context: { target?: string; findings?: any[] }) {
  const r = await api.post('/ai/recommendations', context)
  return r.data
}

export async function executeAIWorkflow(workflow: {
  type: string
  params: Record<string, any>
}) {
  const r = await api.post('/ai/workflow', workflow)
  return r.data
}

export async function getCopilotChat(organizationId: string, message: string, context?: {
  context_type?: 'asset' | 'exposure' | 'finding' | 'graph'
  context_entity_id?: string
}) {
  const r = await api.post('/copilot/chat', { 
    organization_id: organizationId,
    message,
    ...context 
  })
  return r.data
}

export async function investigateEntity(organizationId: string, data: {
  investigation_type: 'asset' | 'exposure' | 'finding'
  entity_id: string
  analyst_note?: string
}) {
  const r = await api.post('/copilot/investigate', {
    organization_id: organizationId,
    ...data
  })
  return r.data
}

export async function generateInvestigationReport(organizationId: string, investigationData: any) {
  const r = await api.post('/copilot/investigate/report', {
    organization_id: organizationId,
    investigation_data: investigationData
  })
  return r.data
}

export async function getInvestigationHistory(organizationId: string) {
  const r = await api.get('/copilot/history', {
    params: { organization_id: organizationId }
  })
  return r.data
}
