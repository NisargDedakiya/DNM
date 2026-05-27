import { useEffect, useRef, useState, useCallback } from 'react'

export interface WSMessage {
  type: string
  line?: string
  tool?: string
  event?: string
  scan_id?: string
  message?: string
  targets_preview?: string[]
  total_targets?: number
  [key: string]: any
}

interface UseWebSocketOptions {
  /** Called for every parsed JSON message from the server */
  onMessage?: (msg: WSMessage) => void
  /** Maximum reconnect attempts before giving up */
  maxRetries?: number
  /** Delay (ms) between reconnect attempts */
  retryDelay?: number
  /** Auto-connect on mount (default true) */
  autoConnect?: boolean
}

interface UseWebSocketReturn {
  messages: WSMessage[]
  isConnected: boolean
  send: (data: string | object) => void
  connect: () => void
  disconnect: () => void
}

/**
 * Custom hook for WebSocket connections to the scan output stream.
 *
 * Usage:
 * ```tsx
 * const { messages, isConnected } = useWebSocket(scanId, {
 *   onMessage: (msg) => console.log(msg),
 * })
 * ```
 */
export function useWebSocket(
  scanId: string | undefined,
  options: UseWebSocketOptions = {},
): UseWebSocketReturn {
  const {
    onMessage,
    maxRetries = 3,
    retryDelay = 2000,
    autoConnect = true,
  } = options

  const [messages, setMessages] = useState<WSMessage[]>([])
  const [isConnected, setIsConnected] = useState(false)

  const wsRef = useRef<WebSocket | null>(null)
  const retriesRef = useRef(0)
  const timerRef = useRef<ReturnType<typeof setTimeout>>()
  const onMessageRef = useRef(onMessage)
  onMessageRef.current = onMessage

  const getWsUrl = useCallback(() => {
    // Use relative path — Vite proxy handles it in dev
    const protocol = window.location.protocol === 'https:' ? 'wss' : 'ws'
    const host = import.meta.env.VITE_WS_URL
      ? new URL(import.meta.env.VITE_WS_URL).host
      : window.location.host
    return `${protocol}://${host}/ws/${scanId}`
  }, [scanId])

  const connect = useCallback(() => {
    if (!scanId) return
    // Clean up any existing connection
    if (wsRef.current) {
      wsRef.current.close()
      wsRef.current = null
    }

    const url = getWsUrl()
    const ws = new WebSocket(url)

    ws.onopen = () => {
      setIsConnected(true)
      retriesRef.current = 0
    }

    ws.onmessage = (event) => {
      try {
        const parsed: WSMessage = JSON.parse(event.data)
        setMessages((prev) => [...prev, parsed])
        onMessageRef.current?.(parsed)
      } catch {
        // Non-JSON messages → wrap in a generic WSMessage
        const fallback: WSMessage = { type: 'raw', line: event.data }
        setMessages((prev) => [...prev, fallback])
        onMessageRef.current?.(fallback)
      }
    }

    ws.onerror = () => {
      // Will trigger onclose
    }

    ws.onclose = () => {
      setIsConnected(false)
      wsRef.current = null

      // Auto-reconnect
      if (retriesRef.current < maxRetries) {
        retriesRef.current++
        timerRef.current = setTimeout(() => {
          connect()
        }, retryDelay)
      }
    }

    wsRef.current = ws
  }, [scanId, getWsUrl, maxRetries, retryDelay])

  const disconnect = useCallback(() => {
    clearTimeout(timerRef.current)
    retriesRef.current = maxRetries // prevent auto-reconnect
    if (wsRef.current) {
      wsRef.current.close()
      wsRef.current = null
    }
    setIsConnected(false)
  }, [maxRetries])

  const send = useCallback((data: string | object) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(typeof data === 'string' ? data : JSON.stringify(data))
    }
  }, [])

  // Connect on mount / scanId change
  useEffect(() => {
    if (autoConnect && scanId) {
      connect()
    }
    return () => {
      clearTimeout(timerRef.current)
      if (wsRef.current) {
        wsRef.current.close()
        wsRef.current = null
      }
    }
  }, [scanId, autoConnect, connect])

  return { messages, isConnected, send, connect, disconnect }
}

export default useWebSocket
