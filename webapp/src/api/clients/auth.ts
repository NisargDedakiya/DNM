import api from '../client'

export interface LoginRequest {
  username: string
  password: string
}

export interface RegisterRequest {
  username: string
  email: string
  password: string
}

export interface User {
  id: string
  username: string
  email: string
  role?: string
  organization_id?: string
}

export interface LoginResponse {
  access_token: string
  token_type: string
  user: User
}

export async function register(req: RegisterRequest) {
  const r = await api.post('/auth/register', req, { withCredentials: true })
  return r.data as LoginResponse
}

export async function login(req: LoginRequest) {
  // server returns access_token and sets HttpOnly refresh cookie
  const r = await api.post('/auth/login', req, { withCredentials: true })
  return r.data as LoginResponse
}

export async function refreshToken() {
  const r = await api.post('/auth/refresh', {}, { withCredentials: true })
  return r.data as LoginResponse
}

export async function getMe() {
  const r = await api.get('/auth/me')
  return r.data as User
}

export async function logout() {
  await api.post('/auth/logout', {}, { withCredentials: true })
}
