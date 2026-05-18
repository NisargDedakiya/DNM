import React, { useState, useEffect } from 'react';
import { Card, Badge, Button } from '../../components/ui/components';
import { motion } from 'framer-motion';
import { listOrganizations, createOrganization, listMembers, inviteMember } from '../../api/clients/organizations';
import useAuthStore from '../../stores/authStore';

interface Organization {
  id: string
  name: string
  slug: string
  description?: string
  owner_id: string
  member_count?: number
  created_at: string
}

interface TeamMember {
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

const OrganizationsPage: React.FC = () => {
  const { user } = useAuthStore();
  const [organizations, setOrganizations] = useState<Organization[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedOrg, setSelectedOrg] = useState<Organization | null>(null);
  const [members, setMembers] = useState<TeamMember[]>([]);
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [showInviteForm, setShowInviteForm] = useState(false);
  
  const [createForm, setCreateForm] = useState({ name: '', slug: '', description: '' });
  const [inviteForm, setInviteForm] = useState({ email: '', role: 'analyst' as 'owner' | 'admin' | 'analyst' | 'viewer' });

  useEffect(() => {
    loadOrganizations();
  }, []);

  const loadOrganizations = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await listOrganizations();
      setOrganizations(data);
      if (data.length > 0) {
        setSelectedOrg(data[0]);
        loadMembers(data[0].id);
      }
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Failed to load organizations');
    } finally {
      setLoading(false);
    }
  };

  const loadMembers = async (orgId: string) => {
    try {
      const data = await listMembers(orgId);
      setMembers(data);
    } catch (err: any) {
      console.error('Failed to load members:', err);
    }
  };

  const handleCreateOrg = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await createOrganization(createForm);
      setShowCreateForm(false);
      setCreateForm({ name: '', slug: '', description: '' });
      await loadOrganizations();
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Failed to create organization');
    }
  };

  const handleInviteMember = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedOrg) return;
    try {
      await inviteMember(selectedOrg.id, inviteForm);
      setShowInviteForm(false);
      setInviteForm({ email: '', role: 'analyst' });
      await loadMembers(selectedOrg.id);
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Failed to invite member');
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-screen">
        <div className="text-center">
          <div className="animate-spin inline-flex items-center justify-center w-12 h-12 rounded-full bg-primary/20 mb-4">
            <svg className="w-6 h-6 text-primary" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
            </svg>
          </div>
          <p className="text-gray-400">Loading organizations...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold text-white mb-1">Organizations</h1>
          <p className="text-gray-400 text-sm">Manage team workspaces and members.</p>
        </div>
        <Button variant="primary" onClick={() => setShowCreateForm(true)}>
          Create Organization
        </Button>
      </div>

      {error && (
        <motion.div initial={{ opacity: 0, y: -10 }} animate={{ opacity: 1, y: 0 }}
          className="p-3 bg-red-500/10 border border-red-500/30 rounded-lg text-sm text-red-400 flex items-center space-x-2">
          <svg className="w-4 h-4 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          <span>{error}</span>
        </motion.div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Organizations List */}
        <Card className="lg:col-span-1 max-h-96 overflow-y-auto">
          <h2 className="text-lg font-semibold text-white mb-4">Your Workspaces</h2>
          <div className="space-y-2">
            {organizations.map(org => (
              <button
                key={org.id}
                onClick={() => {
                  setSelectedOrg(org);
                  loadMembers(org.id);
                }}
                className={`w-full text-left p-3 rounded-lg transition-all ${
                  selectedOrg?.id === org.id 
                    ? 'bg-primary/20 border border-primary/50 text-white' 
                    : 'bg-white/5 border border-white/10 text-gray-300 hover:bg-white/10'
                }`}
              >
                <div className="font-semibold text-sm">{org.name}</div>
                <div className="text-xs text-gray-400 mt-1">@{org.slug}</div>
                {user?.id === org.owner_id && (
                  <Badge variant="secondary" className="text-xs mt-2">Owner</Badge>
                )}
              </button>
            ))}
          </div>
        </Card>

        {/* Organization Details */}
        {selectedOrg && (
          <Card className="lg:col-span-2">
            <div className="mb-6">
              <h2 className="text-lg font-semibold text-white mb-1">{selectedOrg.name}</h2>
              <p className="text-gray-400 text-sm">{selectedOrg.description}</p>
              <div className="flex items-center space-x-3 mt-3">
                <Badge variant="primary">@{selectedOrg.slug}</Badge>
                {selectedOrg.member_count && (
                  <span className="text-sm text-gray-400">{selectedOrg.member_count} member(s)</span>
                )}
              </div>
            </div>

            <div className="border-t border-white/10 pt-6">
              <div className="flex justify-between items-center mb-4">
                <h3 className="text-sm font-semibold text-gray-300">Team Members</h3>
                <Button variant="outline" onClick={() => setShowInviteForm(true)} className="text-sm px-3 py-1">
                  Invite
                </Button>
              </div>

              <div className="space-y-3">
                {members.length === 0 ? (
                  <p className="text-sm text-gray-500">No members yet.</p>
                ) : (
                  members.map(member => (
                    <div key={member.id} className="flex items-center justify-between p-3 bg-white/5 rounded-lg border border-white/10">
                      <div>
                        <div className="text-sm font-medium text-white">{member.username}</div>
                        <div className="text-xs text-gray-500">{member.email}</div>
                      </div>
                      <Badge variant="outline" className="text-xs">{member.role}</Badge>
                    </div>
                  ))
                )}
              </div>
            </div>
          </Card>
        )}
      </div>

      {/* Create Organization Modal */}
      {showCreateForm && (
        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <Card className="w-full max-w-md">
            <h2 className="text-xl font-bold text-white mb-4">Create Organization</h2>
            <form onSubmit={handleCreateOrg} className="space-y-4">
              <div>
                <label className="text-sm text-gray-300 block mb-2">Organization Name</label>
                <input
                  type="text"
                  value={createForm.name}
                  onChange={e => setCreateForm({...createForm, name: e.target.value})}
                  className="w-full bg-background-card/50 border border-white/10 rounded px-3 py-2 text-white focus:outline-none focus:ring-2 focus:ring-primary/50"
                  placeholder="My Security Team"
                  required
                />
              </div>
              <div>
                <label className="text-sm text-gray-300 block mb-2">Slug (URL-friendly)</label>
                <input
                  type="text"
                  value={createForm.slug}
                  onChange={e => setCreateForm({...createForm, slug: e.target.value})}
                  className="w-full bg-background-card/50 border border-white/10 rounded px-3 py-2 text-white focus:outline-none focus:ring-2 focus:ring-primary/50"
                  placeholder="my-security-team"
                  required
                />
              </div>
              <div>
                <label className="text-sm text-gray-300 block mb-2">Description (Optional)</label>
                <textarea
                  value={createForm.description}
                  onChange={e => setCreateForm({...createForm, description: e.target.value})}
                  rows={3}
                  className="w-full bg-background-card/50 border border-white/10 rounded px-3 py-2 text-white focus:outline-none focus:ring-2 focus:ring-primary/50 resize-none"
                  placeholder="Organization description..."
                />
              </div>
              <div className="flex space-x-3">
                <Button variant="outline" onClick={() => setShowCreateForm(false)} className="flex-1">Cancel</Button>
                <Button variant="primary" type="submit" className="flex-1">Create</Button>
              </div>
            </form>
          </Card>
        </motion.div>
      )}

      {/* Invite Member Modal */}
      {showInviteForm && selectedOrg && (
        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <Card className="w-full max-w-md">
            <h2 className="text-xl font-bold text-white mb-4">Invite Member to {selectedOrg.name}</h2>
            <form onSubmit={handleInviteMember} className="space-y-4">
              <div>
                <label className="text-sm text-gray-300 block mb-2">Email Address</label>
                <input
                  type="email"
                  value={inviteForm.email}
                  onChange={e => setInviteForm({...inviteForm, email: e.target.value})}
                  className="w-full bg-background-card/50 border border-white/10 rounded px-3 py-2 text-white focus:outline-none focus:ring-2 focus:ring-primary/50"
                  placeholder="team@example.com"
                  required
                />
              </div>
              <div>
                <label className="text-sm text-gray-300 block mb-2">Role</label>
                <select
                  value={inviteForm.role}
                  onChange={e => setInviteForm({...inviteForm, role: e.target.value as 'owner' | 'admin' | 'analyst' | 'viewer'})}
                  className="w-full bg-background-card/50 border border-white/10 rounded px-3 py-2 text-white focus:outline-none focus:ring-2 focus:ring-primary/50"
                >
                  <option value="viewer">Viewer (Read-only)</option>
                  <option value="analyst">Analyst (Scans & Findings)</option>
                  <option value="admin">Admin (Full Access)</option>
                  <option value="owner">Owner (Organization)</option>
                </select>
              </div>
              <div className="flex space-x-3">
                <Button variant="outline" onClick={() => setShowInviteForm(false)} className="flex-1">Cancel</Button>
                <Button variant="primary" type="submit" className="flex-1">Invite</Button>
              </div>
            </form>
          </Card>
        </motion.div>
      )}
    </div>
  );
};

export default OrganizationsPage;
