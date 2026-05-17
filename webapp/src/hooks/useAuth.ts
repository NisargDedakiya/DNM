import { useCallback } from 'react'
import { login as apiLogin, logout as apiLogout } from '../api/clients/auth'
import { useAuthStore } from '../stores/authStore'

export function useAuth() {
  const setToken = useAuthStore((s) => s.setToken)
  const setUser = useAuthStore((s) => s.setUser)
  const clear = useAuthStore((s) => s.clear)

  const login = useCallback(async (username: string, password: string) => {
    const data = await apiLogin({ username, password })
    if (data?.access_token) {
      setToken(data.access_token)
    }
    if (data?.user) setUser(data.user)
    return data
  }, [])

  const logout = useCallback(async () => {
    try {
      await apiLogout()
    } finally {
      clear()
    }
  }, [])

  return { login, logout }
}
