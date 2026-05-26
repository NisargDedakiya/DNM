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

export async function getFindings(program_id: string, params?: { severity?: string; status?: string }) {
  const r = await api.get('/findings', { params: { program_id, ...params } })
  return r.data?.findings || r.data || []
}

export async function createFinding(data: {
  program_id: string
  title: string
  description: string
  severity: 'critical' | 'high' | 'medium' | 'low' | 'info'
  endpoint?: string
  evidence?: string
}) {
  const r = await api.post('/findings', data)
  return r.data as Finding
}

export async function updateFinding(
  id: string,
  data: {
    title?: string
    severity?: string
    description?: string
    status?: string
  }
) {
  const r = await api.put(`/findings/${id}`, data)
  return r.data as Finding
}

export async function triageFinding(id: string) {
  const r = await api.post(`/findings/${id}/triage`)
  return r.data
}

export async function getFinding(id: string): Promise<Finding> {
  const r = await api.get(`/findings/${id}`)
  return r.data as Finding
}

export async function confirmFinding(id: string): Promise<Finding> {
  const r = await api.put(`/findings/${id}`, { status: 'confirmed' })
  return r.data as Finding
}

