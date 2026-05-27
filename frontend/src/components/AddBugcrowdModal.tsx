import React, { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { ingestBugcrowdEngagement, BugcrowdAsset } from '../api/clients/bugcrowd'
import { Button, Spinner, Badge } from './ui/components'
import useAuthStore from '../stores/authStore'

interface AddBugcrowdModalProps {
  isOpen: boolean
  onClose: () => void
  onSuccess?: () => void
}

type Step = 'input' | 'preview' | 'success'

export const AddBugcrowdModal: React.FC<AddBugcrowdModalProps> = ({ isOpen, onClose, onSuccess }) => {
  const [step, setStep] = useState<Step>('input')
  const [url, setUrl] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [previewData, setPreviewData] = useState<{
    program_name: string
    assets_count: number
    in_scope: BugcrowdAsset[]
    out_of_scope: BugcrowdAsset[]
    bounty_ranges?: Record<string, string>
  } | null>(null)

  const organizationId = useAuthStore((state) => state.user?.organization_id || '')

  const handleFetchScope = async () => {
    setLoading(true)
    setError(null)
    try {
      const result = await ingestBugcrowdEngagement(organizationId, url)
      if (result.success) {
        setPreviewData({
          program_name: result.program_name,
          assets_count: result.assets_imported,
          in_scope: [],
          out_of_scope: [],
          bounty_ranges: {},
        })
        setStep('preview')
      } else {
        setError(result.message || 'Failed to fetch scope')
      }
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to fetch scope. Check URL.')
    } finally {
      setLoading(false)
    }
  }

  const handleConfirm = async () => {
    setStep('success')
    setTimeout(() => {
      onSuccess?.()
      onClose()
    }, 2000)
  }

  const handleCancel = () => {
    setStep('input')
    setUrl('')
    setPreviewData(null)
    setError(null)
    onClose()
  }

  return (
    <AnimatePresence>
      {isOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center">
          {/* Backdrop */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={handleCancel}
            className="absolute inset-0 bg-black/50 backdrop-blur-sm"
          />

          {/* Modal */}
          <motion.div
            initial={{ opacity: 0, scale: 0.95, y: 20 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95, y: 20 }}
            className="relative glass-panel border border-white/10 rounded-2xl p-8 max-w-2xl w-full mx-4 shadow-2xl"
          >
            {/* Step 1: URL Input */}
            {step === 'input' && (
              <div className="space-y-6">
                <div>
                  <h2 className="text-2xl font-bold text-white mb-2">Add Bugcrowd Program</h2>
                  <p className="text-gray-400">Paste your Bugcrowd engagement URL to import scope</p>
                </div>

                {error && (
                  <motion.div
                    initial={{ opacity: 0, y: -10 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="p-4 bg-red-500/10 border border-red-500/30 rounded-lg text-red-400 text-sm flex items-start space-x-3"
                  >
                    <svg className="w-5 h-5 flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                    </svg>
                    <span>{error}</span>
                  </motion.div>
                )}

                <div>
                  <label htmlFor="url" className="block text-sm font-medium text-gray-300 mb-2">
                    Engagement URL
                  </label>
                  <input
                    id="url"
                    type="url"
                    value={url}
                    onChange={(e) => setUrl(e.target.value)}
                    placeholder="https://bugcrowd.com/programs/..."
                    className="w-full bg-background-card/50 border border-white/10 rounded-lg py-3 px-4 text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-primary/50 focus:border-transparent transition-all"
                  />
                </div>

                <div className="flex justify-end space-x-3">
                  <Button variant="outline" onClick={handleCancel}>
                    Cancel
                  </Button>
                  <Button
                    disabled={!url || loading}
                    onClick={handleFetchScope}
                  >
                    {loading ? (
                      <span className="flex items-center space-x-2">
                        <Spinner className="w-4 h-4" />
                        <span>Fetching Scope...</span>
                      </span>
                    ) : (
                      'Fetch Scope'
                    )}
                  </Button>
                </div>
              </div>
            )}

            {/* Step 2: Scope Preview */}
            {step === 'preview' && previewData && (
              <div className="space-y-6">
                <div>
                  <h2 className="text-2xl font-bold text-white mb-1">{previewData.program_name}</h2>
                  <p className="text-gray-400">Review scope before importing</p>
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div className="p-4 rounded-lg bg-white/5 border border-white/10">
                    <p className="text-gray-400 text-sm mb-1">Total Assets</p>
                    <p className="text-2xl font-bold text-white">{previewData.assets_count}</p>
                  </div>
                  <div className="p-4 rounded-lg bg-white/5 border border-white/10">
                    <p className="text-gray-400 text-sm mb-1">In-Scope</p>
                    <p className="text-2xl font-bold text-primary">{previewData.in_scope.length}</p>
                  </div>
                </div>

                <div>
                  <h3 className="text-sm font-semibold text-white mb-2">In-Scope Assets</h3>
                  <div className="max-h-48 overflow-y-auto space-y-1">
                    {previewData.in_scope.length > 0 ? (
                      previewData.in_scope.map((asset) => (
                        <div key={asset.id} className="text-xs text-green-400 font-mono p-2 bg-green-500/5 border border-green-500/20 rounded">
                          {asset.target}
                        </div>
                      ))
                    ) : (
                      <p className="text-xs text-gray-500">No in-scope assets</p>
                    )}
                  </div>
                </div>

                <div>
                  <h3 className="text-sm font-semibold text-white mb-2">Out-of-Scope Assets</h3>
                  <div className="max-h-24 overflow-y-auto space-y-1">
                    {previewData.out_of_scope.length > 0 ? (
                      previewData.out_of_scope.map((asset) => (
                        <div key={asset.id} className="text-xs text-gray-400 font-mono p-2 bg-white/5 border border-white/10 rounded">
                          {asset.target}
                        </div>
                      ))
                    ) : (
                      <p className="text-xs text-gray-500">No out-of-scope assets</p>
                    )}
                  </div>
                </div>

                <div className="flex justify-end space-x-3 pt-4 border-t border-white/10">
                  <Button
                    variant="outline"
                    onClick={() => setStep('input')}
                  >
                    Back
                  </Button>
                  <Button onClick={handleConfirm}>
                    Confirm & Import
                  </Button>
                </div>
              </div>
            )}

            {/* Step 3: Success */}
            {step === 'success' && (
              <motion.div
                initial={{ opacity: 0, scale: 0.95 }}
                animate={{ opacity: 1, scale: 1 }}
                className="flex flex-col items-center justify-center py-12"
              >
                <motion.div
                  animate={{ scale: [1, 1.1, 1] }}
                  transition={{ duration: 0.5, repeat: 1 }}
                  className="w-16 h-16 rounded-full bg-green-500/20 border border-green-500/30 flex items-center justify-center mb-4"
                >
                  <svg className="w-8 h-8 text-green-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M5 13l4 4L19 7" />
                  </svg>
                </motion.div>
                <h3 className="text-xl font-bold text-white mb-1">Program Imported</h3>
                <p className="text-gray-400">Bugcrowd program has been successfully added.</p>
              </motion.div>
            )}
          </motion.div>
        </div>
      )}
    </AnimatePresence>
  )
}

export default AddBugcrowdModal
