import api from '../client'

// ── Monitoring ──────────────────────────────────────────
export interface MonitoringRule {
  id: string
  organization_id: string
  program_id: string
  name: string
  description?: string
  frequency: 'hourly' | 'daily' | 'weekly'
  enabled: boolean
  created_at: string
}

export interface MonitoringRuleCreate {
  program_id: string
  name: string
  frequency?: 'hourly' | 'daily' | 'weekly'
  description?: string
}

export async function createMonitoringRule(organizationId: string, data: MonitoringRuleCreate) {
  const r = await api.post('/monitoring/rules', data, {
    params: { organization_id: organizationId },
  })
  return r.data as MonitoringRule
}

export async function listMonitoringRules(organizationId: string, params?: { enabled_only?: boolean }) {
  const r = await api.get('/monitoring/rules', {
    params: { organization_id: organizationId, ...params },
  })
  return r.data as MonitoringRule[]
}

export async function updateMonitoringRule(
  organizationId: string,
  ruleId: string,
  data: Partial<MonitoringRuleCreate>
) {
  const r = await api.put(`/monitoring/rules/${ruleId}`, data, {
    params: { organization_id: organizationId },
  })
  return r.data as MonitoringRule
}

export async function deleteMonitoringRule(organizationId: string, ruleId: string) {
  await api.delete(`/monitoring/rules/${ruleId}`, {
    params: { organization_id: organizationId },
  })
}
