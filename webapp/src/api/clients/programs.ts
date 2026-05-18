import api from '../client'

// ── Programs ───────────────────────────────────────────
export interface Program {
  id: string
  name: string
  description?: string
  organization_id?: string
  platform?: string
  scope?: string
  created_at: string
  updated_at: string
  created_by?: string
}

export interface ProgramCreate {
  name: string
  description?: string
  platform?: string
  scope?: string
}

export interface ProgramUpdate {
  name?: string
  description?: string
  platform?: string
  scope?: string
}

export async function createProgram(data: ProgramCreate) {
  const r = await api.post('/programs', data)
  return r.data as Program
}

export async function getPrograms() {
  const r = await api.get('/programs')
  return r.data?.programs || []
}

export async function getProgram(id: string) {
  const r = await api.get(`/programs/${id}`)
  return r.data as Program
}

export async function updateProgram(id: string, data: ProgramUpdate) {
  const r = await api.put(`/programs/${id}`, data)
  return r.data as Program
}

export async function deleteProgram(id: string) {
  await api.delete(`/programs/${id}`)
}

export async function getProgramStats(id: string) {
  const r = await api.get(`/programs/${id}/stats`)
  return r.data
}
