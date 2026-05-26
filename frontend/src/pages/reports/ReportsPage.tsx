import React from 'react';

const ReportsPage: React.FC = () => {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-white mb-2">Total Reports</h1>
        <p className="text-gray-400">Generate and view automated vulnerability reports.</p>
      </div>
      <div className="glass-panel p-6 border border-white/5 flex items-center justify-between">
        <div>
          <h3 className="text-lg font-medium text-white">Comprehensive Recon Report</h3>
          <p className="text-sm text-gray-400">Includes all findings, asset intelligence, and AI Copilot notes.</p>
        </div>
        <button className="px-6 py-2 bg-gradient-to-r from-primary to-secondary text-white font-medium rounded-lg shadow-[0_0_15px_rgba(0,184,255,0.4)]">
          Generate PDF
        </button>
      </div>
    </div>
  );
};

export default ReportsPage;
