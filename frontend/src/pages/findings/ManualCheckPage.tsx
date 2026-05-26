import React, { useState, useEffect } from 'react'
import { useParams, useNavigate, Link } from 'react-router-dom'
import { getVerificationWizard, VerificationWorkflow, VerificationStep } from '../../api/clients/sensei'
import { getFinding, confirmFinding } from '../../api/clients/findings'
import { Badge } from '../../components/ui/components'

export const ManualCheckPage: React.FC = () => {
  const { findingId } = useParams<{ findingId: string }>()
  const navigate = useNavigate()

  const [loading, setLoading] = useState(true)
  const [finding, setFinding] = useState<any | null>(null)
  const [wizard, setWizard] = useState<VerificationWorkflow | null>(null)
  
  // Track completed steps by step_number
  const [completedSteps, setCompletedSteps] = useState<number[]>([])
  
  // Evidence upload state
  const [uploadedFiles, setUploadedFiles] = useState<{ id: string; name: string; type: string; url: string; caption: string }[]>([])
  const [isDragging, setIsDragging] = useState(false)
  const [isSubmitting, setIsSubmitting] = useState(false)

  // Fetch finding and wizard steps
  useEffect(() => {
    if (!findingId) return
    
    const fetchData = async () => {
      try {
        setLoading(true)
        const findingRes = await getFinding(findingId)
        setFinding(findingRes)
        
        const wizardRes = await getVerificationWizard(findingId)
        setWizard(wizardRes)
      } catch (err) {
        console.error('Error fetching verification wizard:', err)
      } finally {
        // Enforce visible animated loading by introducing a small latency
        setTimeout(() => {
          setLoading(false)
        }, 1200)
      }
    }
    
    fetchData()
  }, [findingId])

  // Complete steps toggle
  const toggleStep = (stepNumber: number) => {
    setCompletedSteps(prev => 
      prev.includes(stepNumber) 
        ? prev.filter(n => n !== stepNumber) 
        : [...prev, stepNumber]
    )
  }

  // Handle Drag & Drop events
  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(true)
  }

  const handleDragLeave = () => {
    setIsDragging(false)
  }

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(false)
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      handleFiles(e.dataTransfer.files)
    }
  }

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      handleFiles(e.target.files)
    }
  }

  const handleFiles = (files: FileList) => {
    const validTypes = ['image/png', 'image/jpeg', 'video/mp4']
    Array.from(files).forEach(file => {
      if (validTypes.includes(file.type)) {
        const reader = new FileReader()
        reader.onload = (e) => {
          setUploadedFiles(prev => [...prev, {
            id: Math.random().toString(36).substring(7),
            name: file.name,
            type: file.type,
            url: e.target?.result as string || '',
            caption: ''
          }])
        }
        reader.readAsDataURL(file)
      }
    })
  }

  const handleCaptionChange = (id: string, value: string) => {
    setUploadedFiles(prev => prev.map(f => f.id === id ? { ...f, caption: value } : f))
  }

  const handleRemoveFile = (id: string) => {
    setUploadedFiles(prev => prev.filter(f => f.id !== id))
  }

  // Copy to clipboard helper
  const handleCopy = (text: string) => {
    navigator.clipboard.writeText(text)
    alert('Payload copied to clipboard!')
  }

  // Submit / Confirm finding status
  const handleMarkVerified = async () => {
    if (!findingId) return
    try {
      setIsSubmitting(true)
      await confirmFinding(findingId)
      navigate(`/findings/${findingId}/report`)
    } catch (err) {
      console.error('Failed to mark verified:', err)
      alert('Verification submission failed. Please try again.')
    } finally {
      setIsSubmitting(false)
    }
  }

  // Enrichment step generator mapping to return expected payloads and success metrics
  const getEnrichedStep = (step: any) => {
    const vulnType = wizard?.vulnerability_type?.toLowerCase() || 'xss'
    const stepNumber = step.step_number
    
    // Default enrichments
    let action = step.description || step.guidance || 'Perform injection payload check'
    let payload = ''
    let inject_where = 'Tested URL Endpoint Parameter'
    let expected_if_real = 'Vulnerable payload action executed successfully'
    let expected_if_false_positive = 'Input is filtered or rejected with 400 Bad Request / 403 Forbidden'

    if (vulnType.includes('xss')) {
      if (stepNumber === 1) {
        action = 'Identify input reflection field and request type'
        inject_where = 'Search textbox query parameter: ?q='
      } else if (stepNumber === 2) {
        action = 'Send active XSS vector script into URL parameter'
        payload = `<script>alert(document.domain)</script>`
        inject_where = 'URL query field: ?q='
        expected_if_real = 'The browser renders the payload without encoding, showing alert popups.'
        expected_if_false_positive = 'Angle brackets < and > are HTML-encoded into &lt; and &gt;.'
      } else if (stepNumber === 3) {
        action = 'Inspect DOM parsing environment and CORS constraints'
        expected_if_real = 'Script executes within window origin scope; no CSP warning logs present.'
        expected_if_false_positive = 'Content Security Policy (CSP) restricts script eval / execution.'
      }
    } else if (vulnType.includes('idor')) {
      if (stepNumber === 1) {
        action = 'Locate order database reference index parameters'
        inject_where = 'REST API endpoint: GET /api/v1/orders/{order_id}'
      } else if (stepNumber === 2) {
        action = 'Query your own order records profile reference'
        payload = '{"order_id": 9210}'
        inject_where = 'POST request payload'
        expected_if_real = 'Returns data matching user order baseline details'
      } else if (stepNumber === 3) {
        action = 'Modify request order ID to target separate customer orders'
        payload = '{"order_id": 9211}'
        inject_where = 'POST request payload'
        expected_if_real = 'Access granted. Other user records profile details returned.'
        expected_if_false_positive = 'Access denied. Returns 403 Forbidden or 401 Unauthorized.'
      }
    } else {
      // Default fallback payloads
      if (stepNumber === 2) {
        payload = `' OR '1'='1`
        inject_where = 'Login payload parameter'
      }
    }

    return {
      step_number: stepNumber,
      title: step.title || `Verification Step ${stepNumber}`,
      action,
      payload,
      inject_where,
      expected_if_real,
      expected_if_false_positive,
    }
  }

  // Wizard state checks
  const totalSteps = wizard?.verification_steps?.length || 0
  const allStepsCompleted = totalSteps > 0 && completedSteps.length === totalSteps
  const atLeastOneEvidence = uploadedFiles.length >= 1
  const isSubmitEnabled = allStepsCompleted && atLeastOneEvidence

  if (loading) {
    return (
      <div className="min-h-full -m-6 p-8 bg-[#F9FAFB] flex flex-col items-center justify-center relative z-10">
        <div className="flex flex-col items-center justify-center gap-4">
          <div className="flex items-center gap-2">
            <div className="w-4 h-4 bg-[#1B3A6B] rounded-full animate-bounce" style={{ animationDelay: '0s' }} />
            <div className="w-4 h-4 bg-[#1B3A6B] rounded-full animate-bounce" style={{ animationDelay: '0.2s' }} />
            <div className="w-4 h-4 bg-[#1B3A6B] rounded-full animate-bounce" style={{ animationDelay: '0.4s' }} />
          </div>
          <span className="text-sm font-semibold text-gray-500 font-mono">Sensei AI is preparing your validation workbook...</span>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-full -m-6 p-8 bg-[#F9FAFB] text-gray-800 font-sans flex flex-col items-center relative z-10">
      
      {/* Maximum 800px centered page wrapper */}
      <div className="w-full max-w-[800px] flex flex-col gap-6">
        
        {/* Header Breadcrumbs */}
        <div>
          <div className="flex items-center gap-2 text-xs font-bold text-gray-400 uppercase tracking-widest mb-2">
            <Link to="/app" className="hover:text-[#1B3A6B]">Findings</Link>
            <span>&gt;</span>
            <span className="text-gray-500 truncate">{finding?.title || 'Finding'}</span>
            <span>&gt;</span>
            <span className="text-[#1B3A6B]">Manual Check</span>
          </div>
          
          <div className="flex items-center justify-between gap-4">
            <h1 className="text-2xl font-black text-[#1B3A6B]">Verification Wizard</h1>
            <Badge variant={finding?.severity}>{finding?.severity?.toUpperCase()}</Badge>
          </div>
          <div className="text-sm text-gray-400 font-mono mt-2">
            Progress: Step {completedSteps.length} of {totalSteps}
          </div>
        </div>

        {/* Overview Card */}
        <div className="bg-white rounded-xl border border-gray-200 border-l-4 border-l-[#1D4ED8] p-6 shadow-sm flex flex-col gap-3">
          <h3 className="text-sm font-bold text-[#1B3A6B] uppercase tracking-wider">Verification Overview</h3>
          <p className="text-sm text-gray-600 leading-relaxed">
            {finding?.description || 'Manual validation wizard uses AI guided steps to confirm exploitability, filter false positives, and output H1 report reproduction items.'}
          </p>
          <div className="flex items-center gap-4 mt-2 border-t border-gray-100 pt-3">
            <span className="px-2.5 py-1 rounded bg-blue-50 text-blue-700 text-[10px] font-bold uppercase tracking-wider border border-blue-100">
              Estimated Time: 10 mins
            </span>
            <span className="px-2.5 py-1 rounded bg-orange-50 text-orange-700 text-[10px] font-bold uppercase tracking-wider border border-orange-100">
              Difficulty: Intermediate
            </span>
          </div>
        </div>

        {/* Verification Steps List */}
        <div className="flex flex-col gap-6">
          {wizard?.verification_steps.map((rawStep) => {
            const step = getEnrichedStep(rawStep)
            const isCompleted = completedSteps.includes(step.step_number)

            return (
              <div 
                key={step.step_number}
                className={`bg-white rounded-xl border transition-all duration-200 shadow-sm p-6 flex flex-col gap-4 ${
                  isCompleted ? 'border-green-500 bg-green-50/10' : 'border-gray-200'
                }`}
              >
                {/* Step Header */}
                <div className="flex items-start justify-between gap-4">
                  <div className="flex items-center gap-3">
                    <div className="w-8 h-8 rounded-full bg-[#1B3A6B] text-white flex items-center justify-center font-bold text-sm shrink-0">
                      {step.step_number}
                    </div>
                    <h3 className="text-sm font-bold text-gray-800">{step.title}</h3>
                  </div>
                  
                  {/* Step Complete Checkbox */}
                  <label className="flex items-center gap-2 cursor-pointer">
                    <input 
                      type="checkbox"
                      checked={isCompleted}
                      onChange={() => toggleStep(step.step_number)}
                      className="w-4 h-4 accent-green-600 cursor-pointer"
                    />
                    <span className="text-xs font-bold text-gray-500 select-none">Complete</span>
                  </label>
                </div>

                {/* Step Action Text */}
                <p className="text-sm text-gray-600 leading-relaxed pl-11">
                  {step.action}
                </p>

                {/* If Payload Codeblock */}
                {step.payload && (
                  <div className="relative pl-11 mt-1">
                    <pre className="bg-[#1e2937] text-yellow-400 p-4 pr-16 rounded-lg text-xs font-mono overflow-x-auto border border-gray-800">
                      <code>{step.payload}</code>
                    </pre>
                    <button
                      onClick={() => handleCopy(step.payload)}
                      className="absolute top-2.5 right-3 bg-gray-800/80 hover:bg-gray-700 text-white font-mono text-[10px] px-2.5 py-1.5 rounded uppercase font-bold border border-gray-700 transition-colors"
                    >
                      Copy
                    </button>
                  </div>
                )}

                {/* Where to Inject Label */}
                {step.inject_where && (
                  <div className="pl-11 text-xs text-gray-400 font-mono">
                    <span className="font-bold text-gray-500 uppercase tracking-wide">Injection point:</span> {step.inject_where}
                  </div>
                )}

                {/* Success Indicator & False Positive Indicators */}
                <div className="pl-11 grid grid-cols-1 md:grid-cols-2 gap-4 mt-2">
                  <div className="flex items-start gap-2 bg-green-50/50 border border-green-100 p-3 rounded-lg text-xs text-green-800">
                    <span className="text-green-600 font-bold">✓</span>
                    <div>
                      <span className="font-bold">Expected behavior:</span> {step.expected_if_real}
                    </div>
                  </div>

                  <div className="flex items-start gap-2 bg-red-50/50 border border-red-100 p-3 rounded-lg text-xs text-red-800">
                    <span className="text-red-600 font-bold">✗</span>
                    <div>
                      <span className="font-bold">False Positive indicator:</span> {step.expected_if_false_positive}
                    </div>
                  </div>
                </div>

              </div>
            )
          })}
        </div>

        {/* Evidence Upload Section */}
        <div className="bg-white rounded-xl border border-gray-200 p-6 shadow-sm flex flex-col gap-4">
          <div>
            <h3 className="text-base font-bold text-[#1B3A6B] mb-1">Evidence & POC Upload</h3>
            <p className="text-xs text-gray-500">Provide proof-of-concept screenshots or videos verifying the exploit. Minimum 1 file required.</p>
          </div>

          {/* Drag & Drop zone */}
          <div
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onDrop={handleDrop}
            className={`border-2 border-dashed rounded-lg p-8 flex flex-col items-center justify-center gap-2 cursor-pointer transition-colors ${
              isDragging ? 'border-[#1D4ED8] bg-blue-50/20' : 'border-gray-300 hover:border-[#1D4ED8]'
            } ${!allStepsCompleted ? 'opacity-50 cursor-not-allowed' : ''}`}
          >
            <input
              type="file"
              multiple
              accept="image/png, image/jpeg, video/mp4"
              onChange={handleFileSelect}
              disabled={!allStepsCompleted}
              className="hidden"
              id="file-upload"
            />
            <label htmlFor="file-upload" className="flex flex-col items-center justify-center gap-2 cursor-pointer text-center w-full h-full">
              <svg className="w-10 h-10 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.5" d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" /></svg>
              <div>
                <span className="text-sm font-bold text-[#1D4ED8] hover:underline">Click to upload</span> or drag and drop
              </div>
              <span className="text-[10px] text-gray-400">PNG, JPEG, or MP4 formats only</span>
            </label>
          </div>

          {/* Uploaded Thumbnails list */}
          {uploadedFiles.length > 0 && (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-4">
              {uploadedFiles.map((file) => (
                <div key={file.id} className="p-3 rounded-lg border border-gray-200 bg-gray-50 flex flex-col gap-3 relative">
                  <button 
                    onClick={() => handleRemoveFile(file.id)}
                    className="absolute top-2 right-2 text-gray-400 hover:text-red-500 font-bold text-xs p-1"
                  >
                    ✕
                  </button>
                  <div className="flex items-center gap-3">
                    {file.type.startsWith('image/') ? (
                      <img src={file.url} alt={file.name} className="w-12 h-12 object-cover rounded border border-gray-200" />
                    ) : (
                      <div className="w-12 h-12 bg-blue-100 flex items-center justify-center rounded border border-blue-200 text-blue-600 font-mono text-[10px] font-bold">MP4</div>
                    )}
                    <div className="flex-1 min-w-0">
                      <div className="text-xs font-bold text-gray-700 truncate">{file.name}</div>
                      <div className="text-[10px] text-gray-400 uppercase">{file.type.split('/')[1]}</div>
                    </div>
                  </div>
                  <input
                    type="text"
                    value={file.caption}
                    placeholder="Enter evidence caption..."
                    onChange={e => handleCaptionChange(file.id, e.target.value)}
                    className="bg-white border border-gray-200 rounded px-2.5 py-1.5 text-xs text-gray-700 shadow-sm focus:outline-none focus:ring-1 focus:ring-blue-500"
                  />
                </div>
              ))}
            </div>
          )}

        </div>

        {/* Submit Actions */}
        <button
          onClick={handleMarkVerified}
          disabled={!isSubmitEnabled || isSubmitting}
          className={`w-full py-4 text-center rounded-lg text-sm font-bold shadow-md transition-all duration-300 ${
            isSubmitEnabled && !isSubmitting
              ? 'bg-green-600 hover:bg-green-700 text-white cursor-pointer hover:shadow-lg'
              : 'bg-gray-200 text-gray-400 cursor-not-allowed'
          }`}
        >
          {isSubmitting ? 'Submitting Verification...' : 'MARK VERIFIED & SUBMIT'}
        </button>

      </div>

    </div>
  )
}
