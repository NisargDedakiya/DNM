import { create } from 'zustand'
import { persist } from 'zustand/middleware'

export interface User {
  id: string
  username: string
  email?: string
  role?: string
  organization_id?: string
}

export interface Organization {
  id: string
  name: string
  slug: string
  description?: string
  owner_id: string
  created_at?: string
  updated_at?: string
}

export interface AuthState {
  accessToken: string | null
  user: User | null
  isAuthenticated: boolean
  activeOrgId: string | null
  organizations: Organization[]
  setToken: (token: string | null) => void
  setUser: (user: User | null) => void
  setActiveOrgId: (orgId: string | null) => void
  setOrganizations: (organizations: Organization[]) => void
  clear: () => void
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      accessToken: null,
      user: null,
      isAuthenticated: false,
      activeOrgId: null,
      organizations: [],
      setToken: (token) => set(() => ({ accessToken: token, isAuthenticated: !!token })),
      setUser: (user) => set(() => ({ user })),
      setActiveOrgId: (orgId) => set(() => ({ activeOrgId: orgId })),
      setOrganizations: (organizations) => set(() => ({ organizations })),
      clear: () => set(() => ({ accessToken: null, user: null, isAuthenticated: false, activeOrgId: null, organizations: [] })),
    }),
    {
      name: 'nisarg-auth-state',
      partialize: (state) => ({
        accessToken: state.accessToken,
        user: state.user,
        isAuthenticated: state.isAuthenticated,
        activeOrgId: state.activeOrgId,
        organizations: state.organizations,
      }),
    }
  )
)

export const getState = () => {
  const s = useAuthStore.getState()
  return {
    accessToken: s.accessToken,
    activeOrgId: s.activeOrgId,
    setToken: s.setToken,
    clear: s.clear,
  }
}

export default useAuthStore
