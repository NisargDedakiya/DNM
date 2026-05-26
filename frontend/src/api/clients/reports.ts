import api from '../client'

export interface Report {
  id: string
  finding_id: string
  platform: string
  title: string
  severity: string
  vulnerability_type: string
  description: string
  steps_to_reproduce: string[]
  impact: string
  remediation: string
  cvss_score?: number
  quality_score: number
  quality_breakdown: Record<string, number>
  submitted_at?: string
  platform_submission_id?: string
  outcome?: string
}

export interface ReportGenerateRequest {
  finding_id: string
  platform: string
  evidence_notes?: string
}

export interface ReportUpdateRequest {
  title?: string
  severity?: string
  vulnerability_type?: string
  description?: string
  steps_to_reproduce?: string[]
  impact?: string
  remediation?: string
  cvss_score?: number
  quality_score?: number
  quality_breakdown?: Record<string, number>
}

export async function generateReport(request: ReportGenerateRequest): Promise<Report> {
  const r = await api.post('/reports/generate', request)
  return r.data as Report
}

export async function getReport(id: string): Promise<Report> {
  const r = await api.get(`/reports/${id}`)
  return r.data as Report
}

export async function updateReport(id: string, data: ReportUpdateRequest): Promise<Report> {
  const r = await api.put(`/reports/${id}`, data)
  return r.data as Report
}

export async function submitReport(id: string): Promise<{ submission_id: string; status: string }> {
  const r = await api.post(`/reports/${id}/submit`, {})
  return r.data
}
