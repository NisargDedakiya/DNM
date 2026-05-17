import api from '../client'

// ── Findings ─────────────────────────────────────────────
export interface Finding {
  id: string
  title: string
  description: string
  severity: 'critical' | 'high' | 'medium' | 'low' | 'info'
  status: string
  endpoint?: string
  evidence?: string
  program_id: string
  created_at: string
}

export async function getFindings(params?: { program_id?: string; severity?: string; status?: string }) {
  const r = await api.get('/findings/', { params })
  return r.data as Finding[]
}

export async function getFinding(id: string) {
  const r = await api.get(`/findings/${id}`)
  return r.data as Finding
}

export async function triageFinding(finding_id: string) {
  const r = await api.post('/ai/triage', { finding_id })
  return r.data
}

export async function generateReport(finding_ids: string[]) {
  const r = await api.post('/ai/report', { finding_ids })
  return r.data
}
