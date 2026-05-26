import React, { useState, useEffect, useRef } from 'react'
import { useParams, Link } from 'react-router-dom'
import { getScanStatus, pauseScan, ScanStatusResponse, ScanPhase } from '../../api/clients/scans'
import { Badge } from '../../components/ui/components'

export const WorkingStatusPage: React.FC = () => {
  const { scanId } = useParams<{ scanId: string }>()
  const [statusData, setStatusData] = useState<ScanStatusResponse | null>(null)
  const [isPaused, setIsPaused] = useState(false)
  const [logs, setLogs] = useState<{ text: string; severity: string }[]>([])
  const [showAllLogs, setShowAllLogs] = useState(true)
  const [isTerminalCollapsed, setIsTerminalCollapsed] = useState(false)
  const [isHoveringTerminal, setIsHoveringTerminal] = useState(false)
  
  // WebSocket dynamic state updates
  const [liveStats, setLiveStats] = useState({ subdomains: 0, live_hosts: 0, endpoints: 0, findings: 0 })
  const [criticalFindings, setCriticalFindings] = useState<{ title: string; severity: string; confidence: number }[]>([])
  const [wsConnected, setWsConnected] = useState(false)
  
  const terminalEndRef = useRef<HTMLDivElement>(null)

  // Fetch initial scan status
  useEffect(() => {
    if (!scanId) return
    getScanStatus(scanId)
      .then((res) => {
        setStatusData(res)
        setIsPaused(res.status !== 'running')
        setLiveStats(res.stats)
      })
      .catch((err) => console.error('Failed to fetch scan status:', err))
  }, [scanId])

  // WebSocket Connection
  useEffect(() => {
    if (!scanId) return

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const ws = new WebSocket(`${protocol}//localhost:8000/api/ws/${scanId}`)

    ws.onopen = () => {
      setWsConnected(true)
      console.log('Connected to Scan WebSocket')
    }

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)
        if (data.type === 'output') {
          setLogs((prev) => [...prev, { text: data.line, severity: data.severity }])
        } else if (data.type === 'stats') {
          setLiveStats({
            subdomains: data.subdomains,
            live_hosts: data.live_hosts,
            endpoints: data.endpoints,
            findings: data.findings,
          })
        } else if (data.type === 'critical_finding') {
          // Slide in a critical finding card
          setCriticalFindings((prev) => [...prev, {
            title: data.title,
            severity: data.severity,
            confidence: data.confidence
          }])
        }
      } catch (err) {
        console.error('Error parsing WebSocket message:', err)
      }
    }

    ws.onclose = () => {
      setWsConnected(false)
      console.log('Scan WebSocket disconnected')
    }

    return () => {
      ws.close()
    }
  }, [scanId])

  // Auto scroll terminal logs
  useEffect(() => {
    if (!isHoveringTerminal && !isTerminalCollapsed) {
      terminalEndRef.current?.scrollIntoView({ behavior: 'smooth' })
    }
  }, [logs, isHoveringTerminal, isTerminalCollapsed])

  const handlePause = async () => {
    if (!scanId) return
    try {
      const res = await pauseScan(scanId)
      setIsPaused(res.status === 'paused' || res.status === 'pending')
      if (statusData) {
        setStatusData({ ...statusData, status: res.status })
      }
    } catch (err) {
      console.error('Failed to toggle scan status:', err)
    }
  }

  // Filter terminal logs
  const filteredLogs = showAllLogs 
    ? logs 
    : logs.filter(log => log.severity === 'critical' || log.severity === 'warning' || log.severity === 'error')

  // Helper to determine phase status styles
  const getPhaseIcon = (phaseStatus: 'completed' | 'active' | 'pending') => {
    if (phaseStatus === 'completed') {
      return (
        <div className="w-8 h-8 rounded-full bg-green-100 border border-green-500 flex items-center justify-center text-green-600 font-bold">
          ✓
        </div>
      )
    }
    if (phaseStatus === 'active') {
      return (
        <div className="w-8 h-8 rounded-full bg-blue-100 border-2 border-blue-600 border-t-transparent animate-spin flex items-center justify-center text-blue-600" />
      )
    }
    return (
      <div className="w-8 h-8 rounded-full bg-gray-100 border border-gray-300 flex items-center justify-center text-gray-400 font-bold" />
    )
  }

  return (
    <div className="min-h-full -m-6 p-8 bg-[#F9FAFB] text-gray-800 font-sans flex flex-col relative z-10">
      
      {/* Header Row */}
      <div className="flex items-center justify-between border-b border-gray-200 pb-6 mb-8">
        <div>
          <div className="flex items-center gap-3 mb-1">
            <h1 className="text-2xl font-bold text-[#1B3A6B]">Autonomous Hunt Status</h1>
            <span className="px-2.5 py-0.5 rounded-full text-xs font-bold bg-[#1B3A6B]/10 text-[#1B3A6B] border border-[#1B3A6B]/20">
              Active Scan
            </span>
            <span className="px-2.5 py-0.5 rounded-full text-xs font-bold bg-purple-100 text-purple-700 border border-purple-200 animate-pulse">
              STEALTH MODE
            </span>
          </div>
          <p className="text-sm text-gray-500">Scan ID: <span className="font-mono text-gray-600">{scanId}</span></p>
        </div>
        
        <button
          onClick={handlePause}
          className={`flex items-center gap-2 px-5 py-2.5 rounded-lg text-sm font-semibold border transition-all duration-300 shadow-sm ${
            isPaused 
              ? 'bg-green-600 hover:bg-green-700 text-white border-green-700' 
              : 'bg-white hover:bg-gray-50 text-gray-700 border-gray-300'
          }`}
        >
          {isPaused ? (
            <>
              <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20"><path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM9.555 7.168A1 1 0 008 8v4a1 1 0 001.555.832l3-2a1 1 0 000-1.664l-3-2z" clipRule="evenodd" /></svg>
              Resume Scan
            </>
          ) : (
            <>
              <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20"><path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zM7 8a1 1 0 012 0v4a1 1 0 11-2 0V8zm5-1a1 1 0 00-1 1v4a1 1 0 102 0V8a1 1 0 00-1-1z" clipRule="evenodd" /></svg>
              Pause Hunt
            </>
          )}
        </button>
      </div>

      {/* Hunt Pipeline (horizontal) */}
      <div className="bg-white rounded-xl border border-gray-200 p-6 mb-8 shadow-sm">
        <h2 className="text-sm font-bold text-gray-500 uppercase tracking-wider mb-6">Hunt Pipeline</h2>
        <div className="flex items-center justify-between relative">
          
          {/* Connector Line behind steps */}
          <div className="absolute left-6 right-6 top-4 h-[2px] bg-gray-200 -z-1" />

          {statusData?.phases.map((phase: ScanPhase, index: number) => {
            const isCompleted = phase.status === 'completed'
            const isActive = phase.status === 'active'
            
            return (
              <div key={phase.name} className="flex flex-col items-center relative z-10 flex-1">
                {getPhaseIcon(phase.status)}
                <span className={`text-xs font-bold mt-3 ${isActive ? 'text-blue-600' : 'text-gray-500'}`}>
                  {phase.name}
                </span>
                {isActive && (
                  <div className="text-[10px] text-gray-400 font-mono mt-1">
                    {phase.current_tool && <span>{phase.current_tool}</span>}
                    {phase.elapsed && <span className="ml-1">({phase.elapsed})</span>}
                  </div>
                )}
              </div>
            )
          }) || (
            <div className="text-gray-400 text-sm py-4 text-center w-full">Loading pipeline...</div>
          )}

        </div>
      </div>

      {/* Stats Row */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
        <div className="bg-white p-6 rounded-xl border border-gray-200 shadow-sm flex flex-col">
          <span className="text-xs font-bold text-gray-400 uppercase tracking-wider mb-1">Subdomains</span>
          <span className="text-3xl font-extrabold text-[#1B3A6B]">{liveStats.subdomains}</span>
        </div>
        <div className="bg-white p-6 rounded-xl border border-gray-200 shadow-sm flex flex-col">
          <span className="text-xs font-bold text-gray-400 uppercase tracking-wider mb-1">Live Hosts</span>
          <span className="text-3xl font-extrabold text-[#1B3A6B]">{liveStats.live_hosts}</span>
        </div>
        <div className="bg-white p-6 rounded-xl border border-gray-200 shadow-sm flex flex-col">
          <span className="text-xs font-bold text-gray-400 uppercase tracking-wider mb-1">Endpoints</span>
          <span className="text-3xl font-extrabold text-[#1B3A6B]">{liveStats.endpoints}</span>
        </div>
        <div className="bg-white p-6 rounded-xl border border-gray-200 shadow-sm flex flex-col">
          <span className="text-xs font-bold text-gray-400 uppercase tracking-wider mb-1">Findings</span>
          <span className="text-3xl font-extrabold text-red-500">{liveStats.findings}</span>
        </div>
      </div>

      {/* Live Terminal */}
      <div className="bg-[#1e2937] rounded-xl overflow-hidden shadow-lg border border-gray-800 mb-8 transition-all duration-300">
        
        {/* Terminal Header */}
        <div className="bg-[#0f172a] px-5 py-3.5 flex items-center justify-between border-b border-gray-800">
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 rounded-full bg-red-500" />
            <div className="w-3 h-3 rounded-full bg-yellow-500" />
            <div className="w-3 h-3 rounded-full bg-green-500" />
            <span className="text-xs text-gray-400 font-mono ml-2">live-hunt-terminal:~ ({wsConnected ? 'Connected' : 'Reconnecting...'})</span>
          </div>
          
          <div className="flex items-center gap-3">
            <button
              onClick={() => setShowAllLogs(!showAllLogs)}
              className="text-xs font-mono px-3 py-1 rounded bg-gray-800 hover:bg-gray-700 text-gray-300 transition-colors"
            >
              {showAllLogs ? 'Findings Only' : 'Show All'}
            </button>
            <button
              onClick={() => setIsTerminalCollapsed(!isTerminalCollapsed)}
              className="text-xs text-gray-400 hover:text-white p-1"
            >
              {isTerminalCollapsed ? 'Expand ⤓' : 'Collapse ⤒'}
            </button>
          </div>
        </div>

        {/* Terminal logs content */}
        {!isTerminalCollapsed && (
          <div 
            onMouseEnter={() => setIsHoveringTerminal(true)}
            onMouseLeave={() => setIsHoveringTerminal(false)}
            className="h-[300px] overflow-y-auto p-4 font-mono text-sm leading-relaxed text-gray-300 custom-scrollbar flex flex-col gap-1"
          >
            {filteredLogs.length === 0 ? (
              <div className="text-gray-500 text-xs italic">Waiting for terminal stream output logs...</div>
            ) : (
              filteredLogs.map((log, idx) => {
                let colorClass = 'text-gray-400'
                if (log.severity === 'critical' || log.severity === 'error') {
                  colorClass = 'text-red-400 font-semibold'
                } else if (log.severity === 'warning') {
                  colorClass = 'text-yellow-500'
                } else if (log.text.toLowerCase().includes('success') || log.text.toLowerCase().includes('completed')) {
                  colorClass = 'text-green-400'
                }
                return (
                  <div key={idx} className={colorClass}>
                    {log.text}
                  </div>
                )
              })
            )}
            <div ref={terminalEndRef} />
          </div>
        )}
      </div>

      {/* Live Findings Drawer */}
      {criticalFindings.length > 0 && (
        <div className="bg-white rounded-xl border border-gray-200 p-6 shadow-sm flex flex-col gap-4 animate-fade-in mb-6">
          <div className="flex items-center justify-between border-b border-gray-100 pb-3">
            <h3 className="text-base font-bold text-[#1B3A6B]">WebSocket Critical Findings (Live)</h3>
            {statusData && (
              <Link 
                to={`/programs/${statusData.program_id}/findings`}
                className="text-xs font-bold text-blue-600 hover:underline"
              >
                View All Findings →
              </Link>
            )}
          </div>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {criticalFindings.map((finding, index) => (
              <div key={index} className="p-4 rounded-lg border border-red-200 bg-red-50/50 flex flex-col gap-2">
                <div className="flex items-center justify-between">
                  <Badge variant="critical">CRITICAL</Badge>
                  <span className="text-xs font-mono text-gray-500">Conf: {finding.confidence}%</span>
                </div>
                <h4 className="text-sm font-bold text-gray-900">{finding.title}</h4>
                <div className="w-full bg-gray-200 rounded-full h-1.5 mt-2">
                  <div 
                    className="bg-red-500 h-1.5 rounded-full" 
                    style={{ width: `${finding.confidence}%` }}
                  />
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Bottom Button in case findings list is not showing */}
      <div className="flex items-center justify-center mt-4">
        {statusData && (
          <Link
            to={`/programs/${statusData.program_id}/findings`}
            className="px-6 py-3 bg-[#1B3A6B] hover:bg-[#152e54] text-white text-sm font-bold rounded-lg shadow transition-colors"
          >
            Go to Vulnerability Findings
          </Link>
        )}
      </div>

    </div>
  )
}
