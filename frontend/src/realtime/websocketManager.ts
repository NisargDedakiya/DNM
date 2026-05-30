import useRealtimeStore from './realtimeStore'
import { WebSocketMessage } from './eventContracts'
import ReconnectManager from './reconnectManager'

class WebSocketManager {
  private ws: WebSocket | null = null
  private url: string | null = null
  private messageHandlers: Map<string, Array<(data: any) => void>> = new Map()
  private isConnecting = false
  private isConnected = false
  private heartbeatInterval: NodeJS.Timeout | null = null
  private lastHeartbeatAck = Date.now()
  private token: string | null = null
  private orgId: string | null = null
  private reconnectManager: ReconnectManager

  constructor() {
    this.reconnectManager = new ReconnectManager()
    this.reconnectManager.registerReconnect(() => {
      if (this.token && this.orgId) {
        this.connect(this.token, this.orgId, true)
      }
    })
  }

  public connect(token: string, orgId: string, isReconnect = false) {
    if (this.token === token && this.orgId === orgId && (this.isConnected || this.isConnecting)) {
      return
    }

    if (!isReconnect) {
      // Manual/new connection - reset reconnect attempts
      this.reconnectManager.reset()
    }

    this.disconnect(isReconnect)

    this.token = token
    this.orgId = orgId
    this.isConnecting = true

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const host = window.location.host || 'localhost:8000'
    
    // Check if the backend is local dev or production URL
    const baseUrl = import.meta.env.VITE_API_BASE_URL || ''
    let wsHost = host
    if (baseUrl.startsWith('http://') || baseUrl.startsWith('https://')) {
      const parsed = new URL(baseUrl)
      wsHost = parsed.host
    }

    const wsUrl = `${protocol}//${wsHost}/api/ws?token=${token}&org=${orgId}`
    this.url = wsUrl

    console.log('[WebSocketManager] Connecting to WebSocket...')
    try {
      this.ws = new WebSocket(wsUrl)

      this.ws.onopen = () => this.handleOpen()
      this.ws.onmessage = (event) => this.handleMessage(event)
      this.ws.onerror = (error) => this.handleError(error)
      this.ws.onclose = () => this.handleClose()
    } catch (err) {
      this.isConnecting = false
      console.error('[WebSocketManager] WebSocket init error:', err)
      this.scheduleReconnect()
    }
  }

  private handleOpen() {
    this.isConnected = true
    this.isConnecting = false
    this.reconnectManager.reset()
    useRealtimeStore.getState().setConnected(true)
    console.log('[WebSocketManager] Connection established')

    this.startHeartbeat()
    this.emit('connection', { status: 'connected', timestamp: Date.now() })
  }

  private handleMessage(event: MessageEvent) {
    try {
      const data: WebSocketMessage = JSON.parse(event.data)

      if (data.type === 'heartbeat_ack' || data.event_type === 'heartbeat_ack') {
        this.lastHeartbeatAck = Date.now()
        return
      }

      // Add to store's generic event buffer
      useRealtimeStore.getState().addEvent(data)

      // Route message
      const eventType = data.type
      const payload = data.data !== undefined ? data.data : (data.payload !== undefined ? data.payload : data)

      this.emit(eventType, payload)
      this.emit('message', data)
    } catch (err) {
      console.error('[WebSocketManager] Failed to parse message:', err)
    }
  }

  private handleError(error: Event) {
    console.error('[WebSocketManager] Connection error:', error)
    this.emit('error', { error, timestamp: Date.now() })
  }

  private handleClose() {
    console.log('[WebSocketManager] Connection closed')
    this.isConnected = false
    this.isConnecting = false
    useRealtimeStore.getState().setConnected(false)
    this.stopHeartbeat()
    this.emit('connection', { status: 'disconnected', timestamp: Date.now() })
    this.scheduleReconnect()
  }

  private startHeartbeat() {
    this.stopHeartbeat()
    this.lastHeartbeatAck = Date.now()

    this.heartbeatInterval = setInterval(() => {
      if (this.isConnected && this.ws) {
        try {
          this.ws.send(JSON.stringify({ type: 'heartbeat' }))
          if (Date.now() - this.lastHeartbeatAck > 15000) {
            console.warn('[WebSocketManager] Heartbeat timeout. Reconnecting...')
            this.ws.close()
          }
        } catch (err) {
          console.error('[WebSocketManager] Failed to send heartbeat:', err)
        }
      }
    }, 10000)
  }

  private stopHeartbeat() {
    if (this.heartbeatInterval) {
      clearInterval(this.heartbeatInterval)
      this.heartbeatInterval = null
    }
  }

  private scheduleReconnect() {
    if (!this.token || !this.orgId) return
    this.reconnectManager.scheduleReconnect()
  }

  public on(eventType: string, handler: (data: any) => void): () => void {
    if (!this.messageHandlers.has(eventType)) {
      this.messageHandlers.set(eventType, [])
    }
    this.messageHandlers.get(eventType)!.push(handler)

    return () => {
      const handlers = this.messageHandlers.get(eventType) || []
      const idx = handlers.indexOf(handler)
      if (idx > -1) {
        handlers.splice(idx, 1)
      }
    }
  }

  public emit(eventType: string, data: any) {
    const handlers = this.messageHandlers.get(eventType) || []
    handlers.forEach((h) => {
      try {
        h(data)
      } catch (err) {
        console.error(`[WebSocketManager] Handler error for ${eventType}:`, err)
      }
    })
  }

  public send(message: any): boolean {
    if (!this.isConnected || !this.ws) {
      console.warn('[WebSocketManager] Not connected, cannot send')
      return false
    }
    try {
      this.ws.send(JSON.stringify(message))
      return true
    } catch (err) {
      console.error('[WebSocketManager] Send failed:', err)
      return false
    }
  }

  public disconnect(keepCredentials = false) {
    this.stopHeartbeat()
    if (this.ws) {
      // Clear handlers temporarily to prevent callbacks during explicit disconnect
      this.ws.onclose = null
      this.ws.onerror = null
      this.ws.onmessage = null
      this.ws.close()
      this.ws = null
    }
    this.isConnected = false
    this.isConnecting = false
    
    if (!keepCredentials) {
      this.token = null
      this.orgId = null
      this.reconnectManager.reset()
    }
    
    useRealtimeStore.getState().setConnected(false)
    console.log('[WebSocketManager] Disconnected')
  }

  public getStatus() {
    return {
      isConnected: this.isConnected,
      isConnecting: this.isConnecting,
      reconnectAttempts: this.reconnectManager.getAttempts(),
      maxReconnectAttempts: this.reconnectManager.getMaxAttempts(),
      url: this.url,
    }
  }
}

const websocketManager = new WebSocketManager()
export default websocketManager
