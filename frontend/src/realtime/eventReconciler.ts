import websocketManager from './websocketManager'
import cacheSynchronizer from './cacheSynchronizer'
import useRealtimeStore from './realtimeStore'

export function initializeEventReconciler() {
  console.log('[EventReconciler] Initializing event distribution layers...')

  // CRITICAL_ALERT
  websocketManager.on('CRITICAL_ALERT', (data) => {
    console.log('[EventReconciler] Raw Critical Alert:', data)
    useRealtimeStore.getState().addAlert(data)
  })

  // FINDING_UPDATE
  websocketManager.on('FINDING_UPDATE', (data) => {
    console.log('[EventReconciler] Finding Update:', data)
    cacheSynchronizer.invalidateFindings()
    cacheSynchronizer.invalidateGraph()
  })

  // SCAN_UPDATE / hunt_progress
  websocketManager.on('SCAN_UPDATE', (data) => {
    console.log('[EventReconciler] Scan Update:', data)
    cacheSynchronizer.invalidateScans()
  })

  websocketManager.on('hunt_progress', (data) => {
    console.log('[EventReconciler] Hunt Progress:', data)
    cacheSynchronizer.invalidateScans()
  })

  // recon_update
  websocketManager.on('recon_update', (data) => {
    console.log('[EventReconciler] Recon Update:', data)
    cacheSynchronizer.invalidateRecon()
    cacheSynchronizer.invalidateGraph()
    cacheSynchronizer.invalidateAssets()
  })

  // triage_update
  websocketManager.on('triage_update', (data) => {
    console.log('[EventReconciler] Triage Update:', data)
    cacheSynchronizer.invalidateTriage()
    cacheSynchronizer.invalidateFindings()
  })
}
