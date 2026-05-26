import { create } from 'zustand'
import { persist } from 'zustand/middleware'

type User = {
  id: string
  username: string
  email?: string
  role?: string
  organization_id?: string
} | null

type AuthState = {
  accessToken: string | null
  user: User
  isAuthenticated: boolean
  setToken: (token: string | null) => void
  setUser: (u: User) => void
  clear: () => void
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      accessToken: null,
      user: null,
      isAuthenticated: false,
      setToken: (token) => set(() => ({ accessToken: token, isAuthenticated: !!token })),
      setUser: (u) => set(() => ({ user: u })),
      clear: () => set(() => ({ accessToken: null, user: null, isAuthenticated: false })),
    }),
    {
      name: 'nisarg-auth',
      partialize: (state) => ({ accessToken: state.accessToken, user: state.user }),
    }
  )
)

// helper for non-hook usage in api client interceptor
export const getState = () => {
  const s = useAuthStore.getState()
  return {
    accessToken: s.accessToken,
    setToken: s.setToken,
    clear: s.clear,
  }
}

export default useAuthStore
