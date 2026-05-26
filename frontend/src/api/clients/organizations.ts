import api from '../client'

// ── Organizations ────────────────────────────────────────
export interface Organization {
  id: string
  name: string
  slug: string
  description?: string
  owner_id: string
  created_at: string
  updated_at: string
  member_count?: number
}

export interface OrganizationCreate {
  name: string
  slug: string
  description?: string
}

export interface OrganizationUpdate {
  name?: string
  description?: string
}

export interface TeamMember {
  id: string
  user_id: string
  organization_id: string
  role: 'owner' | 'admin' | 'analyst' | 'viewer'
  is_active: boolean
  joined_at: string
  invitation_accepted_at?: string
  username?: string
  email?: string
}

export interface InviteMemberRequest {
  email: string
  role: 'owner' | 'admin' | 'analyst' | 'viewer'
}

export interface UpdateMemberRoleRequest {
  role: 'owner' | 'admin' | 'analyst' | 'viewer'
}

// Create organization
export async function createOrganization(data: OrganizationCreate) {
  const r = await api.post('/organizations', data)
  return r.data as Organization
}

// List user's organizations
export async function listOrganizations() {
  const r = await api.get('/organizations')
  return r.data as Organization[]
}

// Get organization details
export async function getOrganization(id: string) {
  const r = await api.get(`/organizations/${id}`)
  return r.data as Organization
}

// Update organization
export async function updateOrganization(id: string, data: OrganizationUpdate) {
  const r = await api.put(`/organizations/${id}`, data)
  return r.data as Organization
}

// List organization members
export async function listMembers(organizationId: string) {
  const r = await api.get(`/organizations/${organizationId}/members`)
  return r.data as TeamMember[]
}

// Invite team member
export async function inviteMember(organizationId: string, data: InviteMemberRequest) {
  const r = await api.post(`/organizations/${organizationId}/members/invite`, data)
  return r.data
}

// Update member role
export async function updateMemberRole(organizationId: string, memberId: string, data: UpdateMemberRoleRequest) {
  const r = await api.put(`/organizations/${organizationId}/members/${memberId}/role`, data)
  return r.data as TeamMember
}

// Remove member
export async function removeMember(organizationId: string, memberId: string) {
  await api.delete(`/organizations/${organizationId}/members/${memberId}`)
}
