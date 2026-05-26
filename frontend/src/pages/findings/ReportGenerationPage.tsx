import React, { useState, useEffect } from 'react'
import { useParams, useNavigate, Link } from 'react-router-dom'
import { generateReport, getReport, updateReport, submitReport, Report } from '../../api/clients/reports'
import { getFinding } from '../../api/clients/findings'
import { getProgram } from '../../api/clients/programs'
import { Badge, Spinner } from '../../components/ui/components'

export const ReportGenerationPage: React.FC = () => {
  const { findingId } = useParams<{ findingId: string }>()
  const navigate = useNavigate()
  
  const [loading, setLoading] = useState(true)
  const [finding, setFinding] = useState<any | null>(null)
  const [report, setReport] = useState<Report | null>(null)
  
  // Form values
  const [title, setTitle] = useState('')
  const [severity, setSeverity] = useState('medium')
  const [vulnType, setVulnType] = useState('')
  const [description, setDescription] = useState('')
  const [steps, setSteps] = useState<string[]>([])
  const [impact, setImpact] = useState('')
  const [remediation, setRemediation] = useState('')
  const [cvssScore, setCvssScore] = useState<number>(5.0)
  const [affectedUrls, setAffectedUrls] = useState<string>('')
  
  // Submit modal and Toast alert
  const [showConfirmModal, setShowConfirmModal] = useState(false)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [showToast, setShowToast] = useState(false)

  // Generate / Load Report on mount
  useEffect(() => {
    if (!findingId) return
    
    const initializeReport = async () => {
      try {
        setLoading(true)
        // Fetch baseline finding
        const findingRes = await getFinding(findingId)
        setFinding(findingRes)

        // Trigger AI Generation POST
        const generated = await generateReport({
          finding_id: findingId,
          platform: 'hackerone'
        })
        
        setReport(generated)
        setTitle(generated.title)
        setSeverity(generated.severity)
        setVulnType(generated.vulnerability_type || 'XSS (Cross-Site Scripting)')
        setDescription(generated.description)
        setSteps(generated.steps_to_reproduce || ['Navigate to target', 'Inject payload', 'Verify trigger'])
        setImpact(generated.impact)
        setRemediation(generated.remediation)
        setCvssScore(generated.cvss_score || 5.0)
        setAffectedUrls(findingRes.endpoint || 'https://target.com/api/v1')
      } catch (err) {
        console.error('Failed to initialize report:', err)
      } finally {
        setLoading(false)
      }
    }
    
    initializeReport()
  }, [findingId])

  // Quality score breakdown calculation (each field max 20 pts)
  const scoreBreakdown = {
    title: title.length >= 15 ? 20 : Math.round((title.length / 15) * 20),
    steps: steps.length >= 3 ? 20 : Math.round((steps.length / 3) * 20),
    impact: impact.length >= 80 ? 20 : Math.round((impact.length / 80) * 20),
    evidence: 20, // default/verified evidence
    remediation: remediation.length >= 60 ? 20 : Math.round((remediation.length / 60) * 20)
  }

  const totalScore = scoreBreakdown.title + scoreBreakdown.steps + scoreBreakdown.impact + scoreBreakdown.evidence + scoreBreakdown.remediation

  const getScoreColor = (score: number) => {
    if (score >= 85) return 'text-green-600 border-green-200 bg-green-50'
    if (score >= 70) return 'text-orange-600 border-orange-200 bg-orange-50'
    return 'text-red-600 border-red-200 bg-red-50'
  }

  const handleStepChange = (index: number, val: string) => {
    const updated = [...steps]
    updated[index] = val
    setSteps(updated)
  }

  const addStep = () => {
    setSteps([...steps, ''])
  }

  const removeStep = (index: number) => {
    setSteps(steps.filter((_, i) => i !== index))
  }

  // Trigger H1 Submission
  const handleConfirmSubmit = async () => {
    if (!report) return
    try {
      setIsSubmitting(true)
      // Call PUT endpoint to save edits before submission
      await updateReport(report.id, {
        title,
        severity,
        vulnerability_type: vulnType,
        description,
        steps_to_reproduce: steps,
        impact,
        remediation,
        cvss_score: cvssScore,
        quality_score: totalScore
      })

      // Call H1 submit POST
      await submitReport(report.id)
      
      setShowConfirmModal(false)
      setShowToast(true)
      setTimeout(() => {
        setShowToast(false)
        navigate(`/programs/${finding.program_id}/findings`)
      }, 3000)
    } catch (err) {
      console.error('Failed to submit report:', err)
      alert('HackerOne submission failed. Please verify that the program has a HackerOne handle.')
    } finally {
      setIsSubmitting(false)
    }
  }

  if (loading) {
    return (
      <div className="min-h-full -m-6 p-8 bg-[#F9FAFB] flex flex-col items-center justify-center relative z-10">
        <div className="flex flex-col items-center justify-center gap-4">
          <Spinner className="w-10 h-10 text-[#1B3A6B]" />
          <span className="text-sm font-semibold text-gray-500 font-mono">Generating your report with AI...</span>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-full -m-6 p-8 bg-[#F9FAFB] text-gray-800 font-sans flex flex-col relative z-10">
      
      {/* Toast Alert */}
      {showToast && (
        <div className="fixed top-6 right-6 bg-green-600 text-white px-6 py-4 rounded-xl shadow-lg flex items-center gap-3 z-50 animate-fade-in border border-green-700">
          <svg className="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M5 13l4 4L19 7" /></svg>
          <span className="text-sm font-bold">Report submitted successfully to HackerOne!</span>
        </div>
      )}

      {/* Sticky Top Header bar */}
      <div className="sticky top-20 bg-[#F9FAFB]/95 backdrop-blur-md border-b border-gray-200 pb-5 mb-8 z-30 flex items-center justify-between gap-6">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 text-xs font-bold text-gray-400 uppercase tracking-widest mb-1.5">
            <Link to={`/programs/${finding?.program_id}/findings`} className="hover:text-[#1B3A6B]">Findings</Link>
            <span>&gt;</span>
            <span className="text-[#1B3A6B]">HackerOne Report Builder</span>
          </div>
          <input
            type="text"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            className="w-full bg-transparent border-b border-dashed border-gray-300 hover:border-gray-400 focus:border-blue-500 focus:outline-none text-2xl font-black text-[#1B3A6B] py-0.5 truncate"
            placeholder="Edit report title..."
          />
        </div>

        <div className="flex items-center gap-4 shrink-0">
          <div className={`border p-2.5 rounded-lg text-center flex flex-col justify-center ${getScoreColor(totalScore)}`}>
            <span className="text-xl font-black font-mono leading-none">{totalScore}</span>
            <span className="text-[9px] font-bold uppercase tracking-wider mt-1">Quality Score</span>
          </div>

          <button
            onClick={() => setShowConfirmModal(true)}
            disabled={totalScore < 70}
            className={`px-6 py-3.5 rounded-lg text-sm font-bold shadow-md transition-all duration-300 ${
              totalScore >= 70
                ? 'bg-blue-600 hover:bg-blue-700 text-white cursor-pointer hover:shadow-lg'
                : 'bg-gray-200 text-gray-400 cursor-not-allowed'
            }`}
          >
            SUBMIT TO HACKERONE
          </button>
        </div>
      </div>

      {/* Main Form/Preview 2-Column Split */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start mb-8">
        
        {/* Left Column Form (55%) */}
        <div className="lg:col-span-7 flex flex-col gap-6 bg-white p-6 rounded-xl border border-gray-200 shadow-sm">
          
          <h2 className="text-base font-bold text-[#1B3A6B] border-b border-gray-100 pb-3 mb-2">Report Content Editor</h2>
          
          {/* Severity & Type Row */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div className="flex flex-col gap-1.5">
              <label className="text-xs font-bold text-gray-400 uppercase tracking-wider">Severity</label>
              <select
                value={severity}
                onChange={e => setSeverity(e.target.value)}
                className="bg-[#F9FAFB] border border-gray-200 rounded-lg px-3 py-2 text-sm text-gray-700 focus:outline-none focus:ring-1 focus:ring-blue-500"
              >
                <option value="critical">Critical</option>
                <option value="high">High</option>
                <option value="medium">Medium</option>
                <option value="low">Low</option>
                <option value="info">Info</option>
              </select>
            </div>

            <div className="flex flex-col gap-1.5 md:col-span-2">
              <label className="text-xs font-bold text-gray-400 uppercase tracking-wider">Vulnerability Type</label>
              <input
                type="text"
                value={vulnType}
                onChange={e => setVulnType(e.target.value)}
                className="bg-[#F9FAFB] border border-gray-200 rounded-lg px-3 py-2 text-sm text-gray-700 focus:outline-none focus:ring-1 focus:ring-blue-500"
                placeholder="e.g. Cross-Site Scripting (XSS)"
              />
            </div>
          </div>

          {/* Description Textarea */}
          <div className="flex flex-col gap-1.5">
            <label className="text-xs font-bold text-gray-400 uppercase tracking-wider">Description</label>
            <textarea
              value={description}
              onChange={e => setDescription(e.target.value)}
              rows={6}
              className="bg-[#F9FAFB] border border-gray-200 rounded-lg p-3 text-sm text-gray-700 focus:outline-none focus:ring-1 focus:ring-blue-500 leading-relaxed"
              placeholder="Provide a detailed technical description of the vulnerability..."
            />
          </div>

          {/* Steps to Reproduce */}
          <div className="flex flex-col gap-2">
            <div className="flex items-center justify-between border-b border-gray-100 pb-1">
              <label className="text-xs font-bold text-gray-400 uppercase tracking-wider">Steps to Reproduce</label>
              <button
                onClick={addStep}
                className="text-xs font-bold text-blue-600 hover:underline"
              >
                + Add Step
              </button>
            </div>
            <div className="flex flex-col gap-3">
              {steps.map((step, idx) => (
                <div key={idx} className="flex items-start gap-2">
                  <span className="w-6 h-6 rounded-full bg-gray-100 text-gray-500 flex items-center justify-center font-bold text-xs mt-1.5 shrink-0">
                    {idx + 1}
                  </span>
                  <input
                    type="text"
                    value={step}
                    onChange={e => handleStepChange(idx, e.target.value)}
                    className="flex-1 bg-[#F9FAFB] border border-gray-200 rounded-lg px-3 py-2 text-sm text-gray-700 focus:outline-none focus:ring-1 focus:ring-blue-500"
                    placeholder="Enter replication step..."
                  />
                  <button
                    onClick={() => removeStep(idx)}
                    className="text-gray-400 hover:text-red-500 text-xs p-2.5 mt-0.5"
                  >
                    ✕
                  </button>
                </div>
              ))}
            </div>
          </div>

          {/* Impact Textarea */}
          <div className="flex flex-col gap-1.5">
            <label className="text-xs font-bold text-gray-400 uppercase tracking-wider">Impact</label>
            <textarea
              value={impact}
              onChange={e => setImpact(e.target.value)}
              rows={4}
              className="bg-[#F9FAFB] border border-gray-200 rounded-lg p-3 text-sm text-gray-700 focus:outline-none focus:ring-1 focus:ring-blue-500 leading-relaxed"
              placeholder="Explain the security implications and risk of this vulnerability..."
            />
          </div>

          {/* Affected URLs & CVSS */}
          <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
            <div className="flex flex-col gap-1.5 md:col-span-3">
              <label className="text-xs font-bold text-gray-400 uppercase tracking-wider">Affected URLs</label>
              <input
                type="text"
                value={affectedUrls}
                onChange={e => setAffectedUrls(e.target.value)}
                className="bg-[#F9FAFB] border border-gray-200 rounded-lg px-3 py-2 text-sm text-gray-700 focus:outline-none focus:ring-1 focus:ring-blue-500 font-mono"
              />
            </div>
            
            <div className="flex flex-col gap-1.5">
              <label className="text-xs font-bold text-gray-400 uppercase tracking-wider">CVSS Score</label>
              <input
                type="number"
                step="0.1"
                min="0"
                max="10"
                value={cvssScore}
                onChange={e => setCvssScore(parseFloat(e.target.value) || 5.0)}
                className="bg-[#F9FAFB] border border-gray-200 rounded-lg px-3 py-2 text-sm text-gray-700 focus:outline-none focus:ring-1 focus:ring-blue-500 font-mono"
              />
            </div>
          </div>

          {/* Remediation Textarea */}
          <div className="flex flex-col gap-1.5">
            <label className="text-xs font-bold text-gray-400 uppercase tracking-wider">Remediation</label>
            <textarea
              value={remediation}
              onChange={e => setRemediation(e.target.value)}
              rows={3}
              className="bg-[#F9FAFB] border border-gray-200 rounded-lg p-3 text-sm text-gray-700 focus:outline-none focus:ring-1 focus:ring-blue-500 leading-relaxed"
              placeholder="Specify the remediation steps or code fix recommended..."
            />
          </div>

        </div>

        {/* Right Column Preview (45% sticky) */}
        <div className="lg:col-span-5 lg:sticky lg:top-56 flex flex-col gap-4">
          
          {/* HackerOne Preview Card */}
          <div className="bg-[#0b1020] text-gray-200 p-6 rounded-xl border border-gray-800 shadow-lg flex flex-col gap-5">
            <div className="flex items-center justify-between border-b border-gray-800 pb-3">
              <span className="text-xs font-bold text-blue-400 font-mono uppercase tracking-wider">HackerOne Platform View</span>
              <Badge variant={severity === 'critical' || severity === 'high' ? 'critical' : 'medium'}>{severity?.toUpperCase()}</Badge>
            </div>

            <div className="flex flex-col gap-4 max-h-[500px] overflow-y-auto custom-scrollbar pr-2">
              <div>
                <h1 className="text-xl font-bold text-white mb-1">{title || 'Vulnerability Report Title'}</h1>
                <div className="text-xs text-gray-400 font-mono">Type: {vulnType} | CVSS: {cvssScore}</div>
              </div>

              <div>
                <h3 className="text-xs font-bold text-blue-400 uppercase tracking-wider mb-1 font-mono"># Description</h3>
                <p className="text-xs text-gray-300 whitespace-pre-wrap leading-relaxed bg-[#111827] p-3 rounded border border-gray-800 font-mono">
                  {description || 'No description entered.'}
                </p>
              </div>

              <div>
                <h3 className="text-xs font-bold text-blue-400 uppercase tracking-wider mb-1 font-mono"># Steps to Reproduce</h3>
                <ol className="text-xs text-gray-300 list-decimal pl-5 flex flex-col gap-1.5">
                  {steps.map((step, idx) => (
                    <li key={idx} className="font-mono bg-[#111827] p-2 rounded border border-gray-800">{step || 'Step description'}</li>
                  ))}
                </ol>
              </div>

              <div>
                <h3 className="text-xs font-bold text-blue-400 uppercase tracking-wider mb-1 font-mono"># Impact</h3>
                <p className="text-xs text-gray-300 whitespace-pre-wrap leading-relaxed bg-[#111827] p-3 rounded border border-gray-800 font-mono">
                  {impact || 'No impact assessment entered.'}
                </p>
              </div>

              <div>
                <h3 className="text-xs font-bold text-blue-400 uppercase tracking-wider mb-1 font-mono"># Affected URLs</h3>
                <code className="text-xs text-yellow-400 block bg-[#111827] p-2.5 rounded border border-gray-800 font-mono break-all">{affectedUrls || 'https://'}</code>
              </div>

              <div>
                <h3 className="text-xs font-bold text-blue-400 uppercase tracking-wider mb-1 font-mono"># Remediation</h3>
                <p className="text-xs text-gray-300 whitespace-pre-wrap leading-relaxed bg-[#111827] p-3 rounded border border-gray-800 font-mono">
                  {remediation || 'No remediation recommended yet.'}
                </p>
              </div>
            </div>
          </div>

          {/* Quality Score Auditor details */}
          <div className="bg-white p-6 rounded-xl border border-gray-200 shadow-sm flex flex-col gap-4">
            <h3 className="text-sm font-bold text-[#1B3A6B] border-b border-gray-100 pb-2">Report Audit Summary</h3>
            <div className="flex flex-col gap-2.5 text-xs text-gray-600">
              
              <div className="flex justify-between items-center">
                <span>Title Length & Clarity</span>
                <span className={`font-bold ${scoreBreakdown.title === 20 ? 'text-green-600' : 'text-gray-500'}`}>{scoreBreakdown.title}/20</span>
              </div>
              {scoreBreakdown.title < 20 && (
                <div className="text-[10px] text-orange-500 font-semibold bg-orange-50 px-2 py-1 rounded">Tip: Make the title descriptive and include the bug type</div>
              )}

              <div className="flex justify-between items-center">
                <span>Detailed Replication Steps</span>
                <span className={`font-bold ${scoreBreakdown.steps === 20 ? 'text-green-600' : 'text-gray-500'}`}>{scoreBreakdown.steps}/20</span>
              </div>
              {scoreBreakdown.steps < 20 && (
                <div className="text-[10px] text-orange-500 font-semibold bg-orange-50 px-2 py-1 rounded">Tip: Write at least 3 detailed reproduction steps</div>
              )}

              <div className="flex justify-between items-center">
                <span>Business Impact Explanation</span>
                <span className={`font-bold ${scoreBreakdown.impact === 20 ? 'text-green-600' : 'text-gray-500'}`}>{scoreBreakdown.impact}/20</span>
              </div>
              {scoreBreakdown.impact < 20 && (
                <div className="text-[10px] text-orange-500 font-semibold bg-orange-50 px-2 py-1 rounded">Tip: Expand on the confidentiality/integrity threat risk</div>
              )}

              <div className="flex justify-between items-center">
                <span>Manual Verification Proof (Evidence)</span>
                <span className="font-bold text-green-600">{scoreBreakdown.evidence}/20</span>
              </div>

              <div className="flex justify-between items-center">
                <span>Remediation Advice</span>
                <span className={`font-bold ${scoreBreakdown.remediation === 20 ? 'text-green-600' : 'text-gray-500'}`}>{scoreBreakdown.remediation}/20</span>
              </div>
              {scoreBreakdown.remediation < 20 && (
                <div className="text-[10px] text-orange-500 font-semibold bg-orange-50 px-2 py-1 rounded">Tip: Advise specific security headers or filtering syntax fixes</div>
              )}

            </div>

            {totalScore < 70 && (
              <div className="mt-2 bg-red-50 border border-red-200 text-red-800 p-3 rounded-lg text-xs font-bold text-center">
                Report quality score is below the 70% threshold required to submit to HackerOne.
              </div>
            )}
          </div>

        </div>

      </div>

      {/* Confirmation Modal */}
      {showConfirmModal && (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-xl border border-gray-200 shadow-xl max-w-md w-full p-6 flex flex-col gap-4">
            <h3 className="text-lg font-bold text-[#1B3A6B]">Confirm Submission</h3>
            <p className="text-sm text-gray-600 leading-relaxed">
              You are about to submit the report <strong>"{title}"</strong> to the program scope on HackerOne. This will create a official vulnerability ticket.
            </p>
            <div className="flex items-center gap-3 justify-end mt-4">
              <button
                onClick={() => setShowConfirmModal(false)}
                className="px-4 py-2 border border-gray-300 rounded text-xs font-bold text-gray-700 hover:bg-gray-50 transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={handleConfirmSubmit}
                disabled={isSubmitting}
                className="px-5 py-2.5 bg-blue-600 hover:bg-blue-700 text-white rounded text-xs font-bold shadow-sm transition-colors"
              >
                {isSubmitting ? 'Submitting...' : 'Confirm Submit'}
              </button>
            </div>
          </div>
        </div>
      )}

    </div>
  )
}
