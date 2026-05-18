import api from '../client'

// ── Integrations ──────────────────────────────────────
export interface HackerOneProgram {
  id: string
  handle: string
  name: string
  bounty_enabled: boolean
  offers_bounties: boolean
  synced_at: string
}

export interface PlatformProgram {
  id: string
  platform_name: string
  program_name: string
  scope: string
  is_active: boolean
}

export async function syncHackerOne(organizationId: string) {
  const r = await api.post('/integrations/hackerone/sync', {}, {
    params: { organization_id: organizationId }
  })
  return r.data
}

export async function syncBugcrowd(organizationId: string) {
  const r = await api.post('/integrations/bugcrowd/sync', {}, {
    params: { organization_id: organizationId }
  })
  return r.data
}

export async function listIntegratedPrograms(organizationId: string, platform?: string) {
  const r = await api.get('/integrations/programs', {
    params: { organization_id: organizationId, platform }
  })
  return r.data as PlatformProgram[]
}

// HackerOne specific endpoints
export async function connectHackerOne(organizationId: string, credentials: { username: string; api_token: string }) {
  const r = await api.post('/hackerone/connect', {
    organization_id: organizationId,
    ...credentials
  })
  return r.data
}

export async function syncHackerOnePrograms(organizationId: string, credentials: { username: string; api_token: string }) {
  const r = await api.post('/hackerone/sync', {
    organization_id: organizationId,
    ...credentials
  })
  return r.data
}

export async function listHackerOnePrograms(organizationId: string) {
  const r = await api.get('/hackerone/programs', {
    params: { organization_id: organizationId }
  })
  return r.data as { programs: HackerOneProgram[]; total: number }
}

export async function getHackerOneReports(organizationId: string, credentials: { username: string; api_token: string }) {
  const r = await api.get('/hackerone/reports', {
    params: { organization_id: organizationId },
    headers: {
      'X-HackerOne-Username': credentials.username,
      'X-HackerOne-Token': credentials.api_token
    }
  })
  return r.data
}

export async function disconnectIntegration(platform: string) {
  const r = await api.post(`/integrations/${platform}/disconnect`, {})
  return r.data
}
