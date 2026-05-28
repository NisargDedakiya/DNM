import queryClient from '../api/queryClient'

export const cacheSynchronizer = {
  invalidateFindings: () => {
    queryClient.invalidateQueries({ queryKey: ['findings'] })
  },
  invalidateScans: () => {
    queryClient.invalidateQueries({ queryKey: ['scans'] })
    queryClient.invalidateQueries({ queryKey: ['hunts'] })
  },
  invalidateRecon: () => {
    queryClient.invalidateQueries({ queryKey: ['recon'] })
  },
  invalidateTriage: () => {
    queryClient.invalidateQueries({ queryKey: ['triage'] })
  },
  invalidateAssets: () => {
    queryClient.invalidateQueries({ queryKey: ['assets'] })
  },
  invalidateGraph: () => {
    queryClient.invalidateQueries({ queryKey: ['graph'] })
  },
  invalidateCampaigns: () => {
    queryClient.invalidateQueries({ queryKey: ['campaigns'] })
  }
}

export default cacheSynchronizer
