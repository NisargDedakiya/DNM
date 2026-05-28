import useAuthStore from '../state/auth'
import websocketManager from './websocketManager'

let currentToken: string | null = null
let currentOrgId: string | null = null

export function initializeAuthSync() {
  // Subscribe to changes in auth store to automatically manage WebSocket connection
  useAuthStore.subscribe((state) => {
    const { accessToken, activeOrgId } = state
    if (accessToken !== currentToken || activeOrgId !== currentOrgId) {
      currentToken = accessToken
      currentOrgId = activeOrgId

      if (accessToken && activeOrgId) {
        console.log('[AuthSync] Auth state updated, connecting WebSocket...')
        websocketManager.connect(accessToken, activeOrgId)
      } else {
        console.log('[AuthSync] Auth state cleared, disconnecting WebSocket...')
        websocketManager.disconnect()
      }
    }
  })

  // Fire immediately for initial state
  const state = useAuthStore.getState()
  currentToken = state.accessToken
  currentOrgId = state.activeOrgId
  if (currentToken && currentOrgId) {
    websocketManager.connect(currentToken, currentOrgId)
  }
}

