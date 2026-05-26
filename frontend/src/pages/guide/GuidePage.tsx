import React from 'react';

const GuidePage: React.FC = () => {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-white mb-2">Manual Guide</h1>
        <p className="text-gray-400">Documentation and operational playbooks for NisargHunter AI.</p>
      </div>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        <div className="glass-panel p-6 border border-white/5 hover:border-primary/50 transition-colors cursor-pointer">
          <h3 className="text-lg font-medium text-white mb-2">Getting Started</h3>
          <p className="text-sm text-gray-400">Learn how to configure integrations and launch your first AI recon workflow.</p>
        </div>
        <div className="glass-panel p-6 border border-white/5 hover:border-primary/50 transition-colors cursor-pointer">
          <h3 className="text-lg font-medium text-white mb-2">AI Copilot Tactics</h3>
          <p className="text-sm text-gray-400">Advanced usage of the AI Copilot for vulnerability validation.</p>
        </div>
      </div>
    </div>
  );
};

export default GuidePage;
