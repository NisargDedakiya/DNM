import axios from 'axios'
import { getState as getAuthState } from '../stores/authStore'

const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || '/api',
  timeout: 15000,
})

let isRefreshing = false
let failedQueue: any[] = []

const processQueue = (err: any, token: string | null = null) => {
  failedQueue.forEach((prom) => {
    if (err) {
      prom.reject(err)
    } else {
      prom.resolve(token)
    }
  })
  failedQueue = []
}

api.interceptors.request.use((config) => {
  const store = getAuthState()
  const token = store.accessToken
  if (token && config.headers) config.headers['Authorization'] = `Bearer ${token}`
  return config
})

api.interceptors.response.use(
  (res) => res,
  async (err) => {
    const originalRequest = err.config
    if (err.response?.status === 401 && !originalRequest._retry) {
      if (isRefreshing) {
        return new Promise(function (resolve, reject) {
          failedQueue.push({ resolve, reject })
        })
          .then((token) => {
            originalRequest.headers['Authorization'] = `Bearer ${token}`
            return axios(originalRequest)
          })
          .catch((e) => Promise.reject(e))
      }

      originalRequest._retry = true
      isRefreshing = true
      try {
        // call refresh endpoint which uses HttpOnly cookie
        const r = await axios.post((import.meta.env.VITE_API_BASE_URL || '/api') + '/auth/refresh', {}, { withCredentials: true })
        const newToken = r.data?.access_token
        const store = getAuthState()
        store.setToken(newToken)
        processQueue(null, newToken)
        originalRequest.headers['Authorization'] = `Bearer ${newToken}`
        return axios(originalRequest)
      } catch (e) {
        processQueue(e, null)
        // clear auth state
        const store = getAuthState()
        store.clear()
        return Promise.reject(e)
      } finally {
        isRefreshing = false
      }
    }
    return Promise.reject(err)
  }
)

export default api
