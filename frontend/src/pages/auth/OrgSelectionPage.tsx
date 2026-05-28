import React, { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuthStore } from '../../state/auth'
import { listOrganizations, createOrganization } from '../../api/clients/organizations'
import { Button } from '../../components/ui/components'

export const OrgSelectionPage: React.FC = () => {
  const navigate = useNavigate()
  const { setActiveOrgId, setOrganizations, organizations } = useAuthStore()
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [creating, setCreating] = useState(false)
  const [newOrgName, setNewOrgName] = useState('')

  useEffect(() => {
    const fetchOrgs = async () => {
      try {
        const orgs = await listOrganizations()
        setOrganizations(orgs)
        if (orgs.length === 1) {
          setActiveOrgId(orgs[0].id)
          navigate('/app')
        }
      } catch (err: any) {
        setError('Failed to fetch workspaces. Please try again.')
      } finally {
        setLoading(false)
      }
    }
    fetchOrgs()
  }, [setActiveOrgId, setOrganizations, navigate])

  const handleSelect = (orgId: string) => {
    setActiveOrgId(orgId)
    navigate('/app')
  }

  const handleCreateOrg = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!newOrgName.trim()) return
    setCreating(true)
    setError('')
    try {
      const slug = newOrgName.toLowerCase().replace(/[^a-z0-9]+/g, '-')
      const newOrg = await createOrganization({ name: newOrgName, slug })
      setOrganizations([...organizations, newOrg])
      setActiveOrgId(newOrg.id)
      navigate('/app')
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Failed to create workspace.')
    } finally {
      setCreating(false)
    }
  }

  return (
    <div className="min-h-screen bg-background flex flex-col justify-center py-12 sm:px-6 lg:px-8 relative overflow-hidden selection:bg-primary/30">
       <div className="fixed inset-0 z-0 opacity-[0.03] pointer-events-none" 
            style={{ backgroundImage: 'linear-gradient(#00B8FF 1px, transparent 1px), linear-gradient(90deg, #9D4DFF 1px, transparent 1px)', backgroundSize: '60px 60px' }}>
       </div>

       <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-primary/20 rounded-full blur-[120px]" />
       <div className="absolute bottom-1/4 right-1/4 w-96 h-96 bg-secondary/20 rounded-full blur-[120px]" />

       <div className="sm:mx-auto sm:w-full sm:max-w-md relative z-10 text-center">
         <div className="w-20 h-20 mx-auto rounded-2xl bg-gradient-to-br from-primary to-secondary flex items-center justify-center shadow-[0_0_40px_rgba(0,184,255,0.4)] mb-6">
           <svg className="w-10 h-10 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
             <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.5" d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4" />
           </svg>
         </div>
         <h2 className="text-3xl font-extrabold text-white tracking-tight glow-primary">Select Workspace</h2>
         <p className="mt-2 text-sm text-gray-400">Choose the organization segment context for this session</p>
       </div>

       <div className="mt-8 sm:mx-auto sm:w-full sm:max-w-lg relative z-10 px-4">
         <div className="relative group">
           <div className="absolute -inset-[1px] bg-gradient-to-r from-primary to-secondary rounded-2xl opacity-75 blur-sm"></div>
           <div className="relative glass-panel py-8 px-6 shadow-2xl sm:rounded-2xl sm:px-10 border border-white/10 bg-background-card/60 backdrop-blur-xl">
             
             {error && (
               <div className="mb-4 p-3 bg-red-500/10 border border-red-500/30 rounded-lg text-sm text-red-400 flex items-center space-x-2">
                 <span>{error}</span>
               </div>
             )}

             {loading ? (
               <div className="flex flex-col items-center py-12">
                 <svg className="animate-spin h-8 w-8 text-primary mb-3" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                   <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                   <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                 </svg>
                 <span className="text-gray-400 text-sm">Scanning available segments...</span>
               </div>
             ) : (
               <div className="space-y-6">
                 {organizations.length > 0 ? (
                   <div className="grid grid-cols-1 gap-4">
                     {organizations.map((org) => (
                       <button
                         key={org.id}
                         onClick={() => handleSelect(org.id)}
                         className="flex items-center justify-between p-4 bg-background-card/40 hover:bg-background-card/80 border border-white/5 hover:border-primary/40 rounded-xl transition-all duration-300 group/item text-left w-full"
                       >
                         <div>
                           <div className="font-bold text-white group-hover/item:text-primary transition-colors">{org.name}</div>
                           <div className="text-xs text-gray-400 mt-1">{org.description || 'Enterprise cyber operations segment'}</div>
                         </div>
                         <svg className="w-5 h-5 text-gray-500 group-hover/item:text-primary transition-colors transform group-hover/item:translate-x-1 duration-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                           <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 5l7 7-7 7" />
                         </svg>
                       </button>
                     ))}
                   </div>
                 ) : (
                   <div className="text-center py-6 text-gray-400 text-sm">
                     No workspace segments initialized. Please create one below.
                   </div>
                 )}

                 <form onSubmit={handleCreateOrg} className="border-t border-white/10 pt-6 mt-6">
                   <h3 className="text-sm font-semibold text-gray-300 mb-4">Initialize New Segment Workspace</h3>
                   <div className="flex gap-2">
                     <input
                       type="text"
                       required
                       value={newOrgName}
                       onChange={(e) => setNewOrgName(e.target.value)}
                       placeholder="e.g. Threat Intelligence Team"
                       className="block flex-1 bg-background-card/50 border border-white/10 rounded-lg px-3 py-2 text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-primary/50 focus:border-transparent transition-all text-sm"
                     />
                     <Button type="submit" disabled={creating} className="text-sm px-4 py-2">
                       {creating ? 'Initializing...' : 'Create & Join'}
                     </Button>
                   </div>
                 </form>
               </div>
             )}

           </div>
         </div>
       </div>
    </div>
  )
}

export default OrgSelectionPage
