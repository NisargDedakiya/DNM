import websocketManager from './websocketManager'
import cacheSynchronizer from './cacheSynchronizer'
import useRealtimeStore from './realtimeStore'
import useFindingsStore from '../state/findings'
import useCampaignsStore from '../state/campaigns'
import useMonitoringStore from '../state/monitoring'
import useAttackGraphStore from '../state/attackGraph'
import useInvestigationsStore from '../state/investigations'

export function initializeEventReconciler() {
  console.log('[EventReconciler] Initializing event distribution layers...')

  // CRITICAL_ALERT / Alert overlays
  websocketManager.on('CRITICAL_ALERT', (data) => {
    console.log('[EventReconciler] Raw Critical Alert:', data)
    useRealtimeStore.getState().addAlert(data)
  })

  // FINDING_UPDATE
  websocketManager.on('FINDING_UPDATE', (data) => {
    console.log('[EventReconciler] Finding Update:', data)
    
    // Invalidate React Query Cache
    cacheSynchronizer.invalidateFindings()
    cacheSynchronizer.invalidateGraph()

    // Update Zustand Store Reactively
    if (data && data.id) {
      const findingsStore = useFindingsStore.getState()
      const exists = findingsStore.findings.some(f => f.id === data.id)
      if (exists) {
        findingsStore.updateFinding(data.id, data)
      } else {
        findingsStore.addFinding(data)
      }
    }
  })

  // SCAN_UPDATE / SCAN_PROGRESS
  websocketManager.on('SCAN_UPDATE', (data) => {
    console.log('[EventReconciler] Scan Update:', data)
    cacheSynchronizer.invalidateScans()
    
    if (data && data.id) {
      // Update monitoring scans store
      useMonitoringStore.getState().updateScan(data.id, data)
    }
  })

  websocketManager.on('SCAN_PROGRESS', (data) => {
    console.log('[EventReconciler] Scan Progress:', data)
    cacheSynchronizer.invalidateScans()
    
    if (data && data.id) {
      useMonitoringStore.getState().updateScan(data.id, data)
    }
  })

  websocketManager.on('hunt_progress', (data) => {
    console.log('[EventReconciler] Hunt Progress:', data)
    cacheSynchronizer.invalidateScans()
    
    if (data && data.hunt_id) {
      // Map hunt_id progress into monitoring store
      useMonitoringStore.getState().updateScan(data.hunt_id, {
        progress: (data.completed_steps / data.total_steps) * 100,
        status: data.status,
      })
    }
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

    if (data && data.finding_id) {
      useFindingsStore.getState().updateFinding(data.finding_id, {
        status: data.status,
      })
    }
  })

  // Ingestion Pipeline Complete
  websocketManager.on('ingestion_complete', (data) => {
    console.log('[EventReconciler] Ingestion complete:', data)
    cacheSynchronizer.invalidateCampaigns()
    cacheSynchronizer.invalidateAssets()
    cacheSynchronizer.invalidateGraph()
    cacheSynchronizer.invalidateFindings()
  })

  // HackerOne Sync Complete
  websocketManager.on('h1_sync_complete', (data) => {
    console.log('[EventReconciler] HackerOne sync complete:', data)
    cacheSynchronizer.invalidateCampaigns()
    cacheSynchronizer.invalidateAssets()
    cacheSynchronizer.invalidateGraph()
    cacheSynchronizer.invalidateFindings()
  })
}

export default initializeEventReconciler
