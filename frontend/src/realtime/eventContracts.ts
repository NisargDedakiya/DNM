export type WebSocketEventType =
  | 'CRITICAL_ALERT'
  | 'FINDING_UPDATE'
  | 'SCAN_UPDATE'
  | 'recon_update'
  | 'triage_update'
  | 'hunt_progress'
  | 'connection'
  | 'error'
  // ── Ingestion Pipeline Events ──────────────────────
  | 'ingestion_started'
  | 'platform_detected'
  | 'page_fetched'
  | 'scope_extracted'
  | 'ai_validated'
  | 'targets_normalized'
  | 'graph_generated'
  | 'monitoring_active'
  | 'findings_active'
  | 'ingestion_complete'
  | 'ingestion_error'
  // ── HackerOne Pipeline Events ──────────────────────
  | 'h1_sync_started'
  | 'h1_programs_fetched'
  | 'h1_scope_normalized'
  | 'h1_reports_synced'
  | 'h1_sync_complete'
  | 'h1_sync_error'

export interface WebSocketMessage<T = any> {
  type: string   // intentionally broad to support all event types dynamically
  data?: T
  payload?: T
  correlation_id?: string
  timestamp?: number
}

export interface CriticalAlertData {
  id: string
  title: string
  message: string
  severity: 'low' | 'medium' | 'high' | 'critical'
  timestamp: string
}

export interface FindingUpdateData {
  id: string
  title: string
  severity: string
  status: string
  [key: string]: any
}

export interface ScanUpdateData {
  id: string
  status: string
  progress: number
  [key: string]: any
}

export interface ReconUpdateData {
  id: string
  type: string
  data: any
}

export interface TriageUpdateData {
  finding_id: string
  status: string
  notes?: string
}

export interface HuntProgressData {
  hunt_id: string
  status: string
  completed_steps: number
  total_steps: number
}
