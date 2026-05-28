export interface UserContract {
  id: string
  username: string
  email: string
  role?: string
  organization_id?: string
}

export interface OrganizationContract {
  id: string
  name: string
  slug: string
  description?: string
  owner_id: string
  created_at?: string
  updated_at?: string
}

export interface FindingContract {
  id: string
  title: string
  description?: string
  severity: 'low' | 'medium' | 'high' | 'critical'
  status: 'open' | 'triaged' | 'resolved' | 'false_positive'
  asset_id?: string
  organization_id: string
  created_at: string
  updated_at?: string
}

export interface AttackGraphNodeContract {
  id: string
  type: string
  label: string
  data: Record<string, any>
  position?: { x: number; y: number }
}

export interface AttackGraphEdgeContract {
  id: string
  source: string
  target: string
  type?: string
}

export interface InvestigationContract {
  id: string
  title: string
  status: 'active' | 'archived' | 'completed'
  created_at: string
  updated_at?: string
  findings_count: number
  creator_id: string
}

export interface EvidenceContract {
  id: string
  investigation_id: string
  type: 'log' | 'screenshot' | 'payload' | 'pcap' | 'text'
  content: string
  metadata?: Record<string, any>
  created_at: string
}
