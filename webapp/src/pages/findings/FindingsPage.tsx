import React, { useState, useEffect } from 'react';
import { Card, Badge, Button } from '../../components/ui/components';
import { motion, AnimatePresence } from 'framer-motion';
import { getFindings, triageFinding } from '../../api/clients/findings';
import { getPrograms } from '../../api/clients/programs';

interface Program {
  id: string
  name: string
}

interface Finding {
  id: string
  title: string
  description?: string
  severity: 'critical' | 'high' | 'medium' | 'low' | 'info'
  status: string
  endpoint?: string
  evidence?: string
  program_id: string
  created_at: string
}

const FindingsPage: React.FC = () => {
  const [programs, setPrograms] = useState<Program[]>([])
  const [selectedProgram, setSelectedProgram] = useState<string | null>(null)
  const [findings, setFindings] = useState<Finding[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [selectedFinding, setSelectedFinding] = useState<Finding | null>(null)
  const [triageLoading, setTriageLoading] = useState(false)

  useEffect(() => {
    loadPrograms()
  }, [])

  useEffect(() => {
    if (selectedProgram) {
      loadFindings()
    }
  }, [selectedProgram])

  const loadPrograms = async () => {
    try {
      setLoading(true)
      setError(null)
      const data = await getPrograms()
      setPrograms(data || [])
      if (data && data.length > 0) {
        setSelectedProgram(data[0].id)
      }
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Failed to load programs')
    } finally {
      setLoading(false)
    }
  }

  const loadFindings = async () => {
    if (!selectedProgram) return
    try {
      setLoading(true)
      setError(null)
      const data = await getFindings(selectedProgram)
      setFindings(data || [])
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Failed to load findings')
    } finally {
      setLoading(false)
    }
  }

  const handleTriage = async () => {
    if (!selectedFinding) return
    try {
      setTriageLoading(true)
      const result = await triageFinding(selectedFinding.id)
      console.log('Triage result:', result)
    } catch (err: any) {
      console.error('Triage error:', err)
    } finally {
      setTriageLoading(false)
    }
  }

  return (
    <div className="space-y-6 relative h-[calc(100vh-8rem)] flex flex-col">
      <div className="flex justify-between items-center shrink-0">
        <div>
          <h1 className="text-2xl font-bold text-white mb-1">Vulnerability Findings</h1>
          <p className="text-gray-400 text-sm">Review, triage, and export AI-verified vulnerabilities.</p>
        </div>
        <div className="flex space-x-3">
          <Button variant="outline" className="px-4 py-2" onClick={loadFindings}>
            <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" /></svg>
            Refresh
          </Button>
          <Button variant="primary" className="px-4 py-2">
            Export Report
          </Button>
        </div>
      </div>

      <Card className="flex-1 flex flex-col min-h-0 p-0 overflow-hidden">
        {loading ? (
          <div className="flex-1 flex items-center justify-center">
            <div className="text-center">
              <div className="inline-flex items-center justify-center w-12 h-12 rounded-full bg-primary/20 animate-pulse mb-4">
                <svg className="w-6 h-6 text-primary animate-spin" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                </svg>
              </div>
              <p className="text-gray-400">Loading findings...</p>
            </div>
          </div>
        ) : error ? (
          <div className="flex-1 flex items-center justify-center">
            <div className="text-center">
              <svg className="w-12 h-12 text-red-400 mx-auto mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 8v4m0 4v.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              <p className="text-gray-400">{error}</p>
              <Button variant="primary" onClick={loadFindings} className="mt-4">Try Again</Button>
            </div>
          </div>
        ) : findings.length === 0 ? (
          <div className="flex-1 flex items-center justify-center">
            <div className="text-center">
              <svg className="w-12 h-12 text-gray-600 mx-auto mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              <p className="text-gray-400">No findings yet. Start a scan to discover vulnerabilities.</p>
            </div>
          </div>
        ) : (
          <div className="overflow-auto flex-1 custom-scrollbar">
            <table className="w-full text-left border-collapse">
              <thead className="bg-white/5 border-b border-white/10 sticky top-0 z-10 backdrop-blur-md">
                <tr>
                  <th className="py-4 px-6 text-sm font-semibold text-gray-300">ID</th>
                  <th className="py-4 px-6 text-sm font-semibold text-gray-300">Title</th>
                  <th className="py-4 px-6 text-sm font-semibold text-gray-300">Endpoint</th>
                  <th className="py-4 px-6 text-sm font-semibold text-gray-300">Severity</th>
                  <th className="py-4 px-6 text-sm font-semibold text-gray-300">Status</th>
                  <th className="py-4 px-6 text-sm font-semibold text-gray-300">Date</th>
                  <th className="py-4 px-6 text-sm font-semibold text-gray-300">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/5">
                {findings.map((finding) => (
                  <tr 
                    key={finding.id} 
                    className={`hover:bg-white/5 transition-colors cursor-pointer ${selectedFinding?.id === finding.id ? 'bg-primary/5' : ''}`}
                    onClick={() => setSelectedFinding(finding)}
                  >
                    <td className="py-4 px-6 font-mono text-sm text-gray-400">{finding.id.substring(0, 8)}</td>
                    <td className="py-4 px-6 text-sm font-medium text-white">{finding.title}</td>
                    <td className="py-4 px-6 font-mono text-sm text-primary hover:underline">{finding.endpoint || '-'}</td>
                    <td className="py-4 px-6">
                      <Badge variant={finding.severity as any} className="uppercase tracking-wider">{finding.severity}</Badge>
                    </td>
                    <td className="py-4 px-6 text-xs text-gray-400">{finding.status}</td>
                    <td className="py-4 px-6 text-sm text-gray-400">{new Date(finding.created_at).toLocaleDateString()}</td>
                    <td className="py-4 px-6">
                      <button className="text-gray-400 hover:text-white transition-colors p-1">
                        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 5l7 7-7 7" /></svg>
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>

      {/* AI Analysis Drawer */}
      <AnimatePresence>
        {selectedFinding && (
          <motion.div 
            initial={{ opacity: 0, x: 400 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: 400 }}
            transition={{ type: 'spring', damping: 25, stiffness: 200 }}
            className="absolute top-0 right-0 h-full w-[500px] glass-card border-l border-white/10 shadow-2xl flex flex-col z-20 rounded-l-2xl rounded-r-none"
          >
            <div className="p-6 border-b border-white/10 flex justify-between items-start">
              <div>
                <div className="flex items-center space-x-3 mb-2">
                  <Badge variant={selectedFinding.severity as any} className="uppercase">{selectedFinding.severity}</Badge>
                  <span className="font-mono text-sm text-gray-400">{selectedFinding.id.substring(0, 8)}</span>
                </div>
                <h2 className="text-xl font-bold text-white">{selectedFinding.title}</h2>
              </div>
              <button 
                onClick={() => setSelectedFinding(null)}
                className="text-gray-400 hover:text-white p-1 rounded-full hover:bg-white/10 transition-colors"
              >
                <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M6 18L18 6M6 6l12 12" /></svg>
              </button>
            </div>

            <div className="p-6 flex-1 overflow-y-auto custom-scrollbar space-y-6">
              <div>
                <h3 className="text-sm font-semibold text-gray-300 mb-2">Description</h3>
                <p className="text-sm text-gray-400">{selectedFinding.description || 'No description available'}</p>
              </div>

              {selectedFinding.evidence && (
                <div>
                  <h3 className="text-sm font-semibold text-gray-300 mb-2">Evidence</h3>
                  <div className="bg-[#0B1020] border border-white/10 rounded-lg p-4 overflow-x-auto font-mono text-xs text-gray-400 max-h-[200px]">
                    <pre>{selectedFinding.evidence}</pre>
                  </div>
                </div>
              )}
              
              <div>
                 <h3 className="text-sm font-semibold text-gray-300 mb-2">Status</h3>
                 <p className="text-sm text-gray-400">{selectedFinding.status}</p>
              </div>
            </div>
            
            <div className="p-6 border-t border-white/10 bg-background-card/80 flex space-x-2">
              <Button 
                variant="primary" 
                className="flex-1"
                onClick={handleTriage}
                disabled={triageLoading}
              >
                {triageLoading ? 'Processing...' : 'Triage with AI'}
              </Button>
              <Button variant="outline" className="flex-1">Export</Button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
};

export default FindingsPage;
