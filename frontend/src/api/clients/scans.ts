import api from '../client'

// ── Scans ─────────────────────────────────────────────
export interface Scan {
  id: string
  name: string
  status: 'pending' | 'running' | 'completed' | 'failed'
  target: string
  scanner_type: string
  created_at: string
  started_at?: string
  completed_at?: string
  progress?: number
  results_count?: number
}

export interface ScanExecutionRequest {
  program_id: string
  target: string
  scanner_type: 'nuclei' | 'subfinder' | 'httpx' | 'katana' | 'ffuf' | 'dalfox' | 'sqlmap'
}

export async function startScan(request: ScanExecutionRequest) {
  const r = await api.post('/scans/start', request)
  return r.data as Scan
}

export async function getScans(params?: { program_id?: string; status?: string }) {
  const r = await api.get('/scans', { params })
  return r.data as Scan[]
}

export async function getScan(id: string) {
  const r = await api.get(`/scans/${id}`)
  return r.data as Scan
}

export async function stopScan(id: string) {
  const r = await api.post(`/scans/${id}/stop`, {})
  return r.data
}

export async function getScanResults(id: string, params?: { limit?: number; offset?: number }) {
  const r = await api.get(`/scans/${id}/results`, { params })
  return r.data
}

export interface ScanPhase {
  name: string
  status: 'completed' | 'active' | 'pending'
  current_tool?: string
  elapsed?: string
}

export interface ScanStatusResponse {
  scan_id: string
  status: string
  current_step: string
  elapsed_time: string
  current_tool?: string
  phases: ScanPhase[]
  stats: {
    subdomains: number
    live_hosts: number
    endpoints: number
    findings: number
  }
}

export async function getScanStatus(scanId: string): Promise<ScanStatusResponse> {
  const r = await api.get(`/scans/${scanId}/status`)
  return r.data as ScanStatusResponse
}

export async function pauseScan(scanId: string): Promise<{ status: string }> {
  const r = await api.post(`/scans/${scanId}/pause`, {})
  return r.data
}

