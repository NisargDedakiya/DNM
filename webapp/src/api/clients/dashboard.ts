import api from '../client'

// ── Dashboard ─────────────────────────────────────────
export interface DashboardStats {
  total_programs: number
  total_scans: number
  total_findings: number
  total_reports: number
  findings_by_severity: Record<string, number>
  active_scans: number
  recent_activity: ActivityItem[]
}

export interface ActivityItem {
  type: string
  id: string
  title?: string
  meta?: Record<string, any>
  created_at: string
}

export async function getDashboardStats() {
  const r = await api.get('/dashboard/stats')
  return r.data as DashboardStats
}

export async function getDashboardActivity(limit: number = 20) {
  const r = await api.get('/dashboard/activity', { params: { limit } })
  return r.data as ActivityItem[]
}

export async function getSeverityBreakdown() {
  const r = await api.get('/dashboard/severity-breakdown')
  return r.data
}

export async function getScanAnalytics(days: number = 7) {
  const r = await api.get('/dashboard/scan-analytics', { params: { days } })
  return r.data
}
