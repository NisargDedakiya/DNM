import api from '../client'

// ── Bugcrowd Engagement Ingestion ──────────────────

export interface BugcrowdIngestionRequest {
  engagement_url: string
  organization_id: string
}

export interface BugcrowdIngestionResult {
  success: boolean
  program_name: string
  program_id: string
  assets_imported: number
  assets_updated: number
  duration_seconds: number
  message: string
}

export interface BugcrowdProgram {
  id: string
  name: string
  engagement_url: string
  status: 'active' | 'closed' | 'pending' | 'archived'
  assets_count: number
  last_synced_at?: string
  created_at: string
  metadata?: {
    bounty_ranges?: Record<string, string>
    asset_categories?: string[]
    auth_required?: boolean
    severity_levels?: Array<{ level: string; bounty?: string }>
  }
}

export interface BugcrowdAsset {
  id: string
  target: string
  type: string
  in_scope: boolean
  wildcard: boolean
  base_domain?: string
  priority?: string
  validation_status: 'pending' | 'valid' | 'invalid'
}

// Ingest a Bugcrowd engagement page with AI-assisted scope extraction
export async function ingestBugcrowdEngagement(
  organizationId: string,
  engagementUrl: string
) {
  const r = await api.post('/integrations/bugcrowd/ingest', {}, {
    params: {
      engagement_url: engagementUrl,
      organization_id: organizationId
    }
  })
  return r.data as BugcrowdIngestionResult
}

// List all ingested Bugcrowd programs for organization
export async function listBugcrowdPrograms(organizationId: string) {
  const r = await api.get('/integrations/bugcrowd/programs', {
    params: { organization_id: organizationId }
  })
  return (r.data?.programs || []) as BugcrowdProgram[]
}

// Get total count of Bugcrowd programs
export async function getBugcrowdProgramCount(organizationId: string) {
  const r = await api.get('/integrations/bugcrowd/programs', {
    params: { organization_id: organizationId }
  })
  return r.data?.total || 0
}

// List extracted assets from a specific Bugcrowd program
export async function listBugcrowdAssets(
  organizationId: string,
  programId: string
) {
  const r = await api.get(`/integrations/bugcrowd/programs/${programId}/assets`, {
    params: { organization_id: organizationId }
  })
  return (r.data?.assets || []) as BugcrowdAsset[]
}

// Get statistics for Bugcrowd ingestion
export async function getBugcrowdStats(organizationId: string) {
  const programs = await listBugcrowdPrograms(organizationId)
  
  let totalAssets = 0
  let inScopeCount = 0
  let criticalAssets = 0
  
  for (const program of programs) {
    const assets = await listBugcrowdAssets(organizationId, program.id)
    totalAssets += assets.length
    inScopeCount += assets.filter(a => a.in_scope).length
    criticalAssets += assets.filter(a => a.priority === 'critical' || a.priority === 'high').length
  }
  
  return {
    total_programs: programs.length,
    total_assets: totalAssets,
    in_scope_assets: inScopeCount,
    priority_assets: criticalAssets,
    last_sync: programs.length > 0 ? programs[0].last_synced_at : null
  }
}
