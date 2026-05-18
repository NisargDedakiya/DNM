/**
 * ManualCheck Component
 * Guided verification workflows for findings validation and evidence tracking
 */

import React, { useState, useEffect } from 'react';
import huntApi from '../services/huntApi';

const ManualCheck = ({ finding, onClose, onVerified }) => {
  const [step, setStep] = useState(0); // 0=intro, 1=checklist, 2=evidence, 3=exploit, 4=confirm
  const [checkedItems, setCheckedItems] = useState([]);
  const [evidence, setEvidence] = useState('');
  const [exploitNotes, setExploitNotes] = useState('');
  const [reproductionSteps, setReproductionSteps] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState(null);
  const [triageReasoning, setTriageReasoning] = useState(null);
  const [loadingReasoning, setLoadingReasoning] = useState(true);

  // Load triage reasoning on mount
  useEffect(() => {
    if (!finding?.id) return;

    const loadReasoning = async () => {
      try {
        const data = await huntApi.getTriageReasoning(finding.id);
        setTriageReasoning(data);
      } catch (err) {
        console.error('Failed to load triage reasoning:', err);
      } finally {
        setLoadingReasoning(false);
      }
    };

    loadReasoning();
  }, [finding?.id]);

  // Verification checklist
  const verificationChecklist = [
    { id: 'access', label: 'Can access the vulnerability' },
    { id: 'reproduce', label: 'Can reproduce the issue' },
    { id: 'impact', label: 'Confirmed impact/damage' },
    { id: 'scope', label: 'Confirmed within scope' },
    { id: 'auth', label: 'Meets auth requirements' },
  ];

  const toggleChecklist = (id) => {
    setCheckedItems((prev) =>
      prev.includes(id) ? prev.filter((item) => item !== id) : [...prev, id]
    );
  };

  const handleSubmit = async () => {
    setIsSubmitting(true);
    setError(null);

    try {
      const verification = {
        checklist: checkedItems,
        evidence,
        exploitation: {
          notes: exploitNotes,
          reproduction_steps: reproductionSteps,
        },
        verified: true,
      };

      await huntApi.submitVerification(finding.id, verification);
      onVerified?.(finding.id);
      onClose();
    } catch (err) {
      console.error('Failed to submit verification:', err);
      setError('Failed to submit verification. Please try again.');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50 p-4">
      <div className="w-full max-w-2xl max-h-[90vh] bg-slate-950 border border-cyan-500/30 rounded-lg overflow-hidden flex flex-col">
        {/* Header */}
        <div className="border-b border-cyan-500/20 bg-slate-900/50 px-6 py-4 flex items-center justify-between">
          <div>
            <h2 className="text-lg font-semibold text-cyan-400">Manual Verification</h2>
            <p className="text-sm text-slate-400 mt-1">{finding?.title}</p>
          </div>
          <button
            onClick={onClose}
            className="text-slate-500 hover:text-slate-300 transition-colors"
          >
            ✕
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-6">
          {/* Step 0: Introduction */}
          {step === 0 && (
            <div className="space-y-4">
              <div className="bg-slate-900/50 border border-cyan-500/20 rounded p-4 mb-6">
                <h3 className="text-cyan-400 font-semibold mb-2">Verification Overview</h3>
                <p className="text-sm text-slate-300 mb-4">
                  This guided workflow will help you verify and document the vulnerability.
                  You'll need to confirm access, reproduce the issue, and provide evidence.
                </p>

                {/* Finding summary */}
                <div className="grid grid-cols-2 gap-3 text-sm">
                  <div>
                    <span className="text-slate-500">Severity:</span>
                    <span className="text-cyan-300 font-mono ml-2">
                      {finding?.severity?.toUpperCase()}
                    </span>
                  </div>
                  <div>
                    <span className="text-slate-500">Confidence:</span>
                    <span className="text-cyan-300 font-mono ml-2">
                      {Math.round(finding?.confidence_score || 0)}%
                    </span>
                  </div>
                </div>
              </div>

              {/* AI Reasoning */}
              {loadingReasoning ? (
                <div className="text-sm text-slate-500">Loading AI reasoning...</div>
              ) : triageReasoning ? (
                <div className="bg-purple-900/20 border border-purple-500/20 rounded p-4">
                  <h4 className="text-purple-400 font-semibold mb-2 text-sm">AI Analysis</h4>
                  <p className="text-sm text-slate-300">{triageReasoning.reasoning}</p>
                </div>
              ) : null}
            </div>
          )}

          {/* Step 1: Verification Checklist */}
          {step === 1 && (
            <div className="space-y-4">
              <h3 className="text-cyan-400 font-semibold mb-4">Verification Checklist</h3>

              <div className="space-y-3">
                {verificationChecklist.map((item) => (
                  <label
                    key={item.id}
                    className="flex items-center gap-3 p-3 bg-slate-900/50 border border-slate-700 rounded hover:border-cyan-500 cursor-pointer transition-all"
                  >
                    <input
                      type="checkbox"
                      checked={checkedItems.includes(item.id)}
                      onChange={() => toggleChecklist(item.id)}
                      className="w-4 h-4 accent-cyan-500"
                    />
                    <span className="text-sm text-slate-300">{item.label}</span>
                  </label>
                ))}
              </div>

              <div className="text-xs text-slate-500 mt-4">
                Checked: {checkedItems.length}/{verificationChecklist.length}
              </div>
            </div>
          )}

          {/* Step 2: Evidence & Documentation */}
          {step === 2 && (
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-semibold text-cyan-400 mb-2">
                  Evidence & Documentation
                </label>
                <textarea
                  value={evidence}
                  onChange={(e) => setEvidence(e.target.value)}
                  placeholder="Paste screenshots, logs, or other evidence here. Include URLs, endpoints, parameters tested, etc."
                  className="w-full h-40 p-3 bg-slate-900 border border-slate-700 rounded text-sm text-slate-300 placeholder-slate-600 focus:outline-none focus:border-cyan-500 font-mono"
                />
              </div>

              <div>
                <label className="block text-sm font-semibold text-cyan-400 mb-2">
                  Reproduction Steps
                </label>
                <textarea
                  value={reproductionSteps}
                  onChange={(e) => setReproductionSteps(e.target.value)}
                  placeholder="1. First step
2. Second step
3. Expected result vs actual result"
                  className="w-full h-32 p-3 bg-slate-900 border border-slate-700 rounded text-sm text-slate-300 placeholder-slate-600 focus:outline-none focus:border-cyan-500 font-mono"
                />
              </div>
            </div>
          )}

          {/* Step 3: Exploitability */}
          {step === 3 && (
            <div className="space-y-4">
              <h3 className="text-cyan-400 font-semibold">Exploitability Review</h3>

              <div className="bg-slate-900/50 border border-slate-700 rounded p-4 space-y-3">
                <div>
                  <label className="block text-sm font-semibold text-slate-300 mb-2">
                    Exploitation Notes
                  </label>
                  <textarea
                    value={exploitNotes}
                    onChange={(e) => setExploitNotes(e.target.value)}
                    placeholder="Describe how the vulnerability could be exploited, impact, business risk, etc."
                    className="w-full h-32 p-3 bg-slate-900 border border-slate-700 rounded text-sm text-slate-300 placeholder-slate-600 focus:outline-none focus:border-cyan-500"
                  />
                </div>

                {/* Quick options */}
                <div className="flex gap-2 flex-wrap">
                  <button
                    onClick={() =>
                      setExploitNotes((prev) =>
                        prev +
                        '\n\n[Potential Impact]\n- Data breach\n- Unauthorized access\n- System compromise'
                      )
                    }
                    className="px-3 py-1.5 bg-slate-800 border border-slate-600 rounded text-xs text-slate-300 hover:border-cyan-500 hover:text-cyan-300 transition-colors"
                  >
                    Add Impact Template
                  </button>
                  <button
                    onClick={() =>
                      setExploitNotes((prev) =>
                        prev +
                        '\n\n[Risk Assessment]\n- Likelihood: High\n- Impact: High\n- Affected Users: Many'
                      )
                    }
                    className="px-3 py-1.5 bg-slate-800 border border-slate-600 rounded text-xs text-slate-300 hover:border-cyan-500 hover:text-cyan-300 transition-colors"
                  >
                    Add Risk Template
                  </button>
                </div>
              </div>
            </div>
          )}

          {/* Step 4: Confirmation */}
          {step === 4 && (
            <div className="space-y-4">
              <h3 className="text-cyan-400 font-semibold mb-4">Verify & Submit</h3>

              {/* Summary */}
              <div className="bg-slate-900/50 border border-slate-700 rounded p-4 space-y-3">
                <div>
                  <span className="text-slate-500 text-sm">Checklist Items:</span>
                  <div className="text-cyan-400 font-mono text-sm mt-1">
                    {checkedItems.length}/{verificationChecklist.length} completed
                  </div>
                </div>

                <div className="h-px bg-slate-700" />

                <div>
                  <span className="text-slate-500 text-sm">Evidence Provided:</span>
                  <div className={`text-sm mt-1 ${evidence ? 'text-green-400' : 'text-red-400'}`}>
                    {evidence ? '✓ Yes' : '✗ No'}
                  </div>
                </div>

                <div className="h-px bg-slate-700" />

                <div>
                  <span className="text-slate-500 text-sm">Exploitation Notes:</span>
                  <div className={`text-sm mt-1 ${exploitNotes ? 'text-green-400' : 'text-red-400'}`}>
                    {exploitNotes ? '✓ Yes' : '✗ No'}
                  </div>
                </div>
              </div>

              {/* Warning */}
              <div className="bg-yellow-900/20 border border-yellow-500/20 rounded p-3">
                <p className="text-sm text-yellow-300">
                  By submitting this verification, you confirm that the vulnerability has been
                  properly validated and the documentation is accurate.
                </p>
              </div>
            </div>
          )}

          {/* Error message */}
          {error && (
            <div className="bg-red-900/20 border border-red-500/30 rounded p-3">
              <p className="text-sm text-red-300">{error}</p>
            </div>
          )}
        </div>

        {/* Footer / Navigation */}
        <div className="border-t border-cyan-500/20 bg-slate-900/50 px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-2">
            {[0, 1, 2, 3, 4].map((i) => (
              <div
                key={i}
                className={`w-2 h-2 rounded-full transition-colors ${
                  i <= step ? 'bg-cyan-500' : 'bg-slate-700'
                }`}
              />
            ))}
          </div>

          <div className="flex gap-2">
            <button
              onClick={onClose}
              className="px-4 py-2 bg-slate-800 border border-slate-700 rounded text-sm text-slate-300 hover:border-slate-600 transition-colors"
            >
              Cancel
            </button>

            {step > 0 && (
              <button
                onClick={() => setStep(step - 1)}
                className="px-4 py-2 bg-slate-800 border border-slate-700 rounded text-sm text-slate-300 hover:border-slate-600 transition-colors"
              >
                Back
              </button>
            )}

            {step < 4 ? (
              <button
                onClick={() => setStep(step + 1)}
                disabled={
                  (step === 1 && checkedItems.length === 0) ||
                  (step === 2 && !evidence && !reproductionSteps)
                }
                className="px-4 py-2 bg-cyan-600 rounded text-sm text-white hover:bg-cyan-500 disabled:bg-slate-700 disabled:text-slate-500 transition-colors"
              >
                Continue
              </button>
            ) : (
              <button
                onClick={handleSubmit}
                disabled={isSubmitting}
                className="px-4 py-2 bg-green-600 rounded text-sm text-white hover:bg-green-500 disabled:bg-slate-700 disabled:text-slate-500 transition-colors"
              >
                {isSubmitting ? 'Submitting...' : 'Submit Verification'}
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default ManualCheck;
