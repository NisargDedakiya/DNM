export const getWebSocketUrl = (token: string, orgId: string): string => {
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  const host = window.location.host || 'localhost:8000'
  
  // Check if the backend is local dev or production URL
  const baseUrl = import.meta.env.VITE_API_BASE_URL || ''
  let wsHost = host
  if (baseUrl.startsWith('http://') || baseUrl.startsWith('https://')) {
    const parsed = new URL(baseUrl)
    wsHost = parsed.host
  }
  
  return `${protocol}//${wsHost}/api/ws?token=${encodeURIComponent(token)}&org=${encodeURIComponent(orgId)}`
}

export const WEBSOCKET_CONFIG = {
  heartbeatIntervalMs: 10000,
  heartbeatTimeoutMs: 15000,
  reconnectDelayMs: 2000,
  maxReconnectDelayMs: 30000,
  maxReconnectAttempts: 15,
}
