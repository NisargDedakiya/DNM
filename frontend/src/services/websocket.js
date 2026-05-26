/**
 * WebSocket Service for Realtime Hunting Operations
 * Handles secure websocket connections, reconnection logic, event subscriptions
 * Maintains operational auditability and workspace isolation
 */

class WebSocketService {
  constructor() {
    this.ws = null;
    this.url = null;
    this.messageHandlers = new Map();
    this.isConnecting = false;
    this.isConnected = false;
    this.reconnectAttempts = 0;
    this.maxReconnectAttempts = 10;
    this.reconnectDelay = 3000; // Start with 3s
    this.maxReconnectDelay = 30000; // Max 30s
    this.heartbeatInterval = null;
    this.lastHeartbeatAck = Date.now();
  }

  /**
   * Initialize WebSocket connection
   * @param {string} token - JWT authentication token
   * @param {string} organizationId - Organization workspace ID
   * @returns {Promise<void>}
   */
  async connect(token, organizationId) {
    if (this.isConnecting || this.isConnected) {
      console.log('[WebSocket] Already connecting or connected');
      return;
    }

    this.isConnecting = true;

    try {
      // Determine WebSocket URL based on environment
      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      const host = window.location.host;
      this.url = `${protocol}//${host}/api/ws?token=${token}&org=${organizationId}`;

      console.log('[WebSocket] Connecting to:', this.url.replace(token, '***'));

      this.ws = new WebSocket(this.url);

      // Setup event handlers
      this.ws.onopen = () => this._handleOpen();
      this.ws.onmessage = (event) => this._handleMessage(event);
      this.ws.onerror = (error) => this._handleError(error);
      this.ws.onclose = () => this._handleClose();

      // Wait for connection to establish
      await this._waitForConnection(5000);

      this.isConnecting = false;
      this.reconnectAttempts = 0;
      this.reconnectDelay = 3000;
    } catch (error) {
      this.isConnecting = false;
      console.error('[WebSocket] Connection failed:', error);
      this._scheduleReconnect();
      throw error;
    }
  }

  /**
   * Handle WebSocket open event
   * @private
   */
  _handleOpen() {
    this.isConnected = true;
    console.log('[WebSocket] Connected successfully');

    // Start heartbeat
    this._startHeartbeat();

    // Emit connected event
    this._emit('connection', { status: 'connected', timestamp: Date.now() });
  }

  /**
   * Handle incoming WebSocket message
   * @private
   */
  _handleMessage(event) {
    try {
      const data = JSON.parse(event.data);

      // Handle heartbeat acknowledgment
      if (data.type === 'heartbeat_ack') {
        this.lastHeartbeatAck = Date.now();
        return;
      }

      // Route message to registered handlers
      const eventType = data.type || 'message';
      const handlers = this.messageHandlers.get(eventType) || [];

      handlers.forEach((handler) => {
        try {
          handler(data.payload || data);
        } catch (error) {
          console.error(`[WebSocket] Handler error for ${eventType}:`, error);
        }
      });

      // Emit generic message event
      this._emit('message', data);
    } catch (error) {
      console.error('[WebSocket] Message parse error:', error);
    }
  }

  /**
   * Handle WebSocket error
   * @private
   */
  _handleError(error) {
    console.error('[WebSocket] Error:', error);
    this._emit('error', { error: error.message, timestamp: Date.now() });
  }

  /**
   * Handle WebSocket close
   * @private
   */
  _handleClose() {
    console.log('[WebSocket] Connection closed');
    this.isConnected = false;
    this._stopHeartbeat();
    this._emit('connection', { status: 'disconnected', timestamp: Date.now() });

    // Attempt reconnection
    this._scheduleReconnect();
  }

  /**
   * Start heartbeat to keep connection alive
   * @private
   */
  _startHeartbeat() {
    this._stopHeartbeat();

    this.heartbeatInterval = setInterval(() => {
      if (this.isConnected && this.ws) {
        try {
          this.ws.send(JSON.stringify({ type: 'heartbeat' }));

          // Check if heartbeat was acknowledged
          const timeSinceAck = Date.now() - this.lastHeartbeatAck;
          if (timeSinceAck > 15000) {
            console.warn('[WebSocket] Heartbeat timeout - reconnecting');
            this.ws.close();
          }
        } catch (error) {
          console.error('[WebSocket] Heartbeat error:', error);
        }
      }
    }, 10000); // Send heartbeat every 10 seconds
  }

  /**
   * Stop heartbeat interval
   * @private
   */
  _stopHeartbeat() {
    if (this.heartbeatInterval) {
      clearInterval(this.heartbeatInterval);
      this.heartbeatInterval = null;
    }
  }

  /**
   * Schedule reconnection with exponential backoff
   * @private
   */
  _scheduleReconnect() {
    if (this.reconnectAttempts >= this.maxReconnectAttempts) {
      console.error('[WebSocket] Max reconnection attempts reached');
      this._emit('error', {
        error: 'Failed to reconnect after multiple attempts',
        fatal: true,
      });
      return;
    }

    this.reconnectAttempts += 1;
    const delay = Math.min(
      this.reconnectDelay * Math.pow(2, this.reconnectAttempts - 1),
      this.maxReconnectDelay
    );

    console.log(
      `[WebSocket] Reconnecting in ${delay}ms (attempt ${this.reconnectAttempts})`
    );

    setTimeout(() => {
      // Get token and org from localStorage (assuming they're stored)
      const token = localStorage.getItem('authToken');
      const organizationId = localStorage.getItem('organizationId');

      if (token && organizationId) {
        this.connect(token, organizationId).catch((error) => {
          console.error('[WebSocket] Reconnection failed:', error);
        });
      }
    }, delay);
  }

  /**
   * Wait for connection to establish with timeout
   * @private
   */
  _waitForConnection(timeout) {
    return new Promise((resolve, reject) => {
      const startTime = Date.now();

      const checkConnection = () => {
        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
          resolve();
        } else if (Date.now() - startTime > timeout) {
          reject(new Error('Connection timeout'));
        } else {
          setTimeout(checkConnection, 100);
        }
      };

      checkConnection();
    });
  }

  /**
   * Subscribe to specific message type
   * @param {string} eventType - Message type to subscribe to
   * @param {Function} handler - Callback function
   * @returns {Function} Unsubscribe function
   */
  on(eventType, handler) {
    if (!this.messageHandlers.has(eventType)) {
      this.messageHandlers.set(eventType, []);
    }

    this.messageHandlers.get(eventType).push(handler);

    // Return unsubscribe function
    return () => {
      const handlers = this.messageHandlers.get(eventType) || [];
      const index = handlers.indexOf(handler);
      if (index > -1) {
        handlers.splice(index, 1);
      }
    };
  }

  /**
   * Subscribe to message type once
   * @param {string} eventType - Message type
   * @param {Function} handler - Callback function
   */
  once(eventType, handler) {
    const unsubscribe = this.on(eventType, (data) => {
      handler(data);
      unsubscribe();
    });
  }

  /**
   * Emit internal event
   * @private
   */
  _emit(eventType, data) {
    const handlers = this.messageHandlers.get(eventType) || [];
    handlers.forEach((handler) => {
      try {
        handler(data);
      } catch (error) {
        console.error(`[WebSocket] Internal event handler error:`, error);
      }
    });
  }

  /**
   * Send message through WebSocket
   * @param {Object} message - Message to send
   * @returns {boolean} Success status
   */
  send(message) {
    if (!this.isConnected || !this.ws) {
      console.warn('[WebSocket] Not connected - cannot send message');
      return false;
    }

    try {
      this.ws.send(JSON.stringify(message));
      return true;
    } catch (error) {
      console.error('[WebSocket] Send error:', error);
      return false;
    }
  }

  /**
   * Subscribe to recon feed updates
   * @param {Function} handler - Callback for recon events
   * @returns {Function} Unsubscribe function
   */
  onReconFeed(handler) {
    return this.on('recon_update', handler);
  }

  /**
   * Subscribe to finding updates
   * @param {Function} handler - Callback for finding events
   * @returns {Function} Unsubscribe function
   */
  onFindingUpdate(handler) {
    return this.on('finding_update', handler);
  }

  /**
   * Subscribe to AI triage updates
   * @param {Function} handler - Callback for triage events
   * @returns {Function} Unsubscribe function
   */
  onTriageUpdate(handler) {
    return this.on('triage_update', handler);
  }

  /**
   * Subscribe to hunt progress updates
   * @param {Function} handler - Callback for progress events
   * @returns {Function} Unsubscribe function
   */
  onHuntProgress(handler) {
    return this.on('hunt_progress', handler);
  }

  /**
   * Subscribe to connection status changes
   * @param {Function} handler - Callback for connection events
   * @returns {Function} Unsubscribe function
   */
  onConnectionStatus(handler) {
    return this.on('connection', handler);
  }

  /**
   * Subscribe to errors
   * @param {Function} handler - Callback for error events
   * @returns {Function} Unsubscribe function
   */
  onError(handler) {
    return this.on('error', handler);
  }

  /**
   * Disconnect WebSocket
   */
  disconnect() {
    this._stopHeartbeat();

    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }

    this.isConnected = false;
    this.isConnecting = false;
    console.log('[WebSocket] Disconnected');
  }

  /**
   * Get connection status
   * @returns {Object} Status information
   */
  getStatus() {
    return {
      isConnected: this.isConnected,
      isConnecting: this.isConnecting,
      reconnectAttempts: this.reconnectAttempts,
      url: this.url ? this.url.replace(/token=.*&/, 'token=***&') : null,
    };
  }
}

// Export singleton instance
export default new WebSocketService();
