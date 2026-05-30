export class ReconnectManager {
  private reconnectAttempts = 0
  private maxReconnectAttempts = 15
  private baseDelay = 2000
  private maxDelay = 30000
  private timeoutId: NodeJS.Timeout | null = null
  private onReconnectCallback: (() => void) | null = null

  constructor(maxAttempts = 15, baseDelay = 2000, maxDelay = 30000) {
    this.maxReconnectAttempts = maxAttempts
    this.baseDelay = baseDelay
    this.maxDelay = maxDelay
  }

  public registerReconnect(callback: () => void) {
    this.onReconnectCallback = callback
  }

  public scheduleReconnect(): boolean {
    if (this.reconnectAttempts >= this.maxReconnectAttempts) {
      console.error('[ReconnectManager] Max reconnection attempts reached')
      return false
    }

    this.reconnectAttempts++
    const delay = Math.min(
      this.baseDelay * Math.pow(1.5, this.reconnectAttempts - 1),
      this.maxDelay
    )
    console.log(`[ReconnectManager] Scheduling reconnection in ${delay}ms (attempt ${this.reconnectAttempts}/${this.maxReconnectAttempts})`)

    if (this.timeoutId) {
      clearTimeout(this.timeoutId)
    }

    this.timeoutId = setTimeout(() => {
      if (this.onReconnectCallback) {
        this.onReconnectCallback()
      }
    }, delay)

    return true
  }

  public reset() {
    this.reconnectAttempts = 0
    if (this.timeoutId) {
      clearTimeout(this.timeoutId)
      this.timeoutId = null
    }
  }

  public getAttempts() {
    return this.reconnectAttempts
  }

  public getMaxAttempts() {
    return this.maxReconnectAttempts
  }
}

export default ReconnectManager
