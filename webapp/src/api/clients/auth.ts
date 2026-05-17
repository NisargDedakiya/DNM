import api from '../client'

export interface LoginRequest {
  username: string
  password: string
}

export async function login(req: LoginRequest) {
  // server returns access_token and sets HttpOnly refresh cookie
  const r = await api.post('/auth/login', req, { withCredentials: true })
  return r.data
}

export async function logout() {
  await api.post('/auth/logout', {}, { withCredentials: true })
}
