/**
 * ReportGeneration Component
 * Report preview, editing, and generation for multiple platforms
 */

import React, { useState, useEffect } from 'react';
import huntApi from '../services/huntApi';

const ReportGeneration = ({ finding, onClose, onSubmit }) => {
  const [reportFormat, setReportFormat] = useState('hackerone');
  const [severity, setSeverity] = useState(finding?.severity || 'high');
  const [report, setReport] = useState('');
  const [remediation, setRemediation] = useState('');
  const [qualityScore, setQualityScore] = useState(0);
  const [loading, setLoading] = useState(true);
  const [isGenerating, setIsGenerating] = useState(false);
  const [error, setError] = useState(null);
  const [editMode, setEditMode] = useState(false);

  // Load report preview on mount
  useEffect(() => {
    if (!finding?.id) return;

    const loadReport = async () => {
      setLoading(true);
      try {
        const data = await huntApi.getReportPreview(finding.id, reportFormat);
        setReport(data.report || '');
        setRemediation(data.remediation || '');
        setQualityScore(data.quality_score || 0);
      } catch (err) {
        console.error('Failed to load report preview:', err);
        setError('Failed to load report');
      } finally {
        setLoading(false);
      }
    };

    loadReport();
  }, [finding?.id, reportFormat]);

  const handleGenerateReport = async () => {
    setIsGenerating(true);
    try {
      const options = {
        severity,
        format: reportFormat,
      };

      const data = await huntApi.generateReport(finding.id, options);
      setReport(data.report || '');
      setRemediation(data.remediation || '');
      setQualityScore(data.quality_score || 0);
    } catch (err) {
      console.error('Failed to generate report:', err);
      setError('Failed to generate report');
    } finally {
      setIsGenerating(false);
    }
  };

  const handleExport = async () => {
    try {
      const blob = await huntApi.exportReport(finding.id, 'markdown');
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${finding.title || 'report'}.md`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (err) {
      console.error('Failed to export report:', err);
      setError('Failed to export report');
    }
  };

  // Calculate quality metrics
  const getQualityColor = (score) => {
    if (score >= 85) return 'text-green-400';
    if (score >= 70) return 'text-yellow-400';
    return 'text-orange-400';
  };

  const getSeverityColor = (sev) => {
    switch (sev?.toLowerCase()) {
      case 'critical':
        return 'bg-red-900/40 text-red-300 border-red-500/30';
      case 'high':
        return 'bg-orange-900/40 text-orange-300 border-orange-500/30';
      case 'medium':
        return 'bg-yellow-900/40 text-yellow-300 border-yellow-500/30';
      case 'low':
        return 'bg-blue-900/40 text-blue-300 border-blue-500/30';
      default:
        return 'bg-slate-900/40 text-slate-300 border-slate-500/30';
    }
  };

  return (
    <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50 p-4">
      <div className="w-full max-w-4xl max-h-[90vh] bg-slate-950 border border-cyan-500/30 rounded-lg overflow-hidden flex flex-col">
        {/* Header */}
        <div className="border-b border-cyan-500/20 bg-slate-900/50 px-6 py-4 flex items-center justify-between">
          <div>
            <h2 className="text-lg font-semibold text-cyan-400">Report Generation</h2>
            <p className="text-sm text-slate-400 mt-1">{finding?.title}</p>
          </div>
          <button
            onClick={onClose}
            className="text-slate-500 hover:text-slate-300 transition-colors"
          >
            ✕
          </button>
        </div>

        {/* Controls */}
        <div className="border-b border-cyan-500/20 bg-slate-900/30 px-6 py-3 flex flex-wrap items-center gap-4">
          {/* Format selector */}
          <div>
            <label className="text-xs text-slate-500 uppercase tracking-wider">Format</label>
            <select
              value={reportFormat}
              onChange={(e) => setReportFormat(e.target.value)}
              className="mt-1 px-3 py-1.5 bg-slate-900 border border-slate-700 rounded text-sm text-slate-300 focus:outline-none focus:border-cyan-500 transition-colors"
            >
              <option value="hackerone">HackerOne</option>
              <option value="bugcrowd">Bugcrowd</option>
              <option value="intigriti">Intigriti</option>
              <option value="markdown">Markdown</option>
            </select>
          </div>

          {/* Severity selector */}
          <div>
            <label className="text-xs text-slate-500 uppercase tracking-wider">Severity</label>
            <select
              value={severity}
              onChange={(e) => setSeverity(e.target.value)}
              className="mt-1 px-3 py-1.5 bg-slate-900 border border-slate-700 rounded text-sm text-slate-300 focus:outline-none focus:border-cyan-500 transition-colors"
            >
              <option value="critical">Critical</option>
              <option value="high">High</option>
              <option value="medium">Medium</option>
              <option value="low">Low</option>
            </select>
          </div>

          {/* Action buttons */}
          <div className="flex gap-2 ml-auto">
            <button
              onClick={handleGenerateReport}
              disabled={isGenerating}
              className="px-4 py-1.5 bg-cyan-600 rounded text-sm text-white hover:bg-cyan-500 disabled:bg-slate-700 disabled:text-slate-500 transition-colors"
            >
              {isGenerating ? 'Generating...' : 'Regenerate'}
            </button>

            <button
              onClick={() => setEditMode(!editMode)}
              className="px-4 py-1.5 bg-slate-800 border border-slate-700 rounded text-sm text-slate-300 hover:border-cyan-500 transition-colors"
            >
              {editMode ? 'View' : 'Edit'}
            </button>

            <button
              onClick={handleExport}
              className="px-4 py-1.5 bg-slate-800 border border-slate-700 rounded text-sm text-slate-300 hover:border-cyan-500 transition-colors"
            >
              Export
            </button>
          </div>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto">
          {loading ? (
            <div className="flex items-center justify-center h-64 text-slate-500">
              <div className="text-center">
                <div className="w-6 h-6 border-2 border-cyan-500 border-t-transparent rounded-full animate-spin mx-auto mb-2" />
                <p className="text-sm">Loading report...</p>
              </div>
            </div>
          ) : (
            <div className="grid grid-cols-2 gap-4 p-6 h-full">
              {/* Report preview/editor */}
              <div className="flex flex-col border border-slate-700 rounded overflow-hidden">
                <div className="bg-slate-900/50 border-b border-slate-700 px-4 py-2">
                  <h3 className="text-sm font-semibold text-cyan-400">Vulnerability Report</h3>
                </div>

                {editMode ? (
                  <textarea
                    value={report}
                    onChange={(e) => setReport(e.target.value)}
                    className="flex-1 p-4 bg-slate-950 text-sm text-slate-300 font-mono border-0 focus:outline-none resize-none"
                  />
                ) : (
                  <div className="flex-1 overflow-auto p-4 text-sm text-slate-300 font-mono whitespace-pre-wrap break-words">
                    {report || 'No report generated'}
                  </div>
                )}
              </div>

              {/* Right panel: Quality score & remediation */}
              <div className="flex flex-col gap-4">
                {/* Quality score */}
                <div className="border border-slate-700 rounded overflow-hidden">
                  <div className="bg-slate-900/50 border-b border-slate-700 px-4 py-2">
                    <h3 className="text-sm font-semibold text-cyan-400">Quality Score</h3>
                  </div>

                  <div className="p-4 space-y-3">
                    <div className="text-center">
                      <div className={`text-4xl font-bold font-mono ${getQualityColor(qualityScore)}`}>
                        {qualityScore}%
                      </div>
                      <p className="text-xs text-slate-500 mt-2">Report Quality</p>
                    </div>

                    {/* Quality indicators */}
                    <div className="space-y-2 pt-2 border-t border-slate-700">
                      <div className="flex items-center justify-between text-xs">
                        <span className="text-slate-500">Technical Accuracy</span>
                        <span className="text-cyan-400">{Math.round(qualityScore * 0.9)}/100</span>
                      </div>
                      <div className="flex items-center justify-between text-xs">
                        <span className="text-slate-500">Documentation</span>
                        <span className="text-cyan-400">{Math.round(qualityScore * 0.85)}/100</span>
                      </div>
                      <div className="flex items-center justify-between text-xs">
                        <span className="text-slate-500">Proof of Concept</span>
                        <span className="text-cyan-400">{Math.round(qualityScore * 0.88)}/100</span>
                      </div>
                    </div>
                  </div>
                </div>

                {/* Remediation */}
                <div className="flex-1 border border-slate-700 rounded overflow-hidden flex flex-col">
                  <div className="bg-slate-900/50 border-b border-slate-700 px-4 py-2">
                    <h3 className="text-sm font-semibold text-cyan-400">Remediation</h3>
                  </div>

                  <div className="flex-1 overflow-auto p-4 text-sm text-slate-300 font-mono whitespace-pre-wrap break-words">
                    {remediation || 'No remediation provided'}
                  </div>
                </div>
              </div>
            </div>
          )}

          {error && (
            <div className="p-6 bg-red-900/20 border border-red-500/30 rounded m-6">
              <p className="text-sm text-red-300">{error}</p>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="border-t border-cyan-500/20 bg-slate-900/50 px-6 py-4 flex items-center justify-between">
          <div className={`text-xs font-mono ${getSeverityColor(severity)}`}>
            {severity.toUpperCase()} · {reportFormat.toUpperCase()}
          </div>

          <div className="flex gap-2">
            <button
              onClick={onClose}
              className="px-4 py-2 bg-slate-800 border border-slate-700 rounded text-sm text-slate-300 hover:border-slate-600 transition-colors"
            >
              Cancel
            </button>

            <button
              onClick={() => onSubmit?.(finding.id)}
              className="px-4 py-2 bg-green-600 rounded text-sm text-white hover:bg-green-500 transition-colors"
            >
              Submit Report
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ReportGeneration;
