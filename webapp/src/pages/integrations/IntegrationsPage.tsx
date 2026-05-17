import React from 'react';

const IntegrationsPage: React.FC = () => {
  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold tracking-wider text-gradient">Integrations</h1>
          <p className="text-gray-400 mt-1">Bug bounty platform connections</p>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {/* HackerOne */}
        <div className="glass-panel p-6 border border-white/10 rounded-xl flex flex-col space-y-4">
          <h2 className="text-lg font-medium text-white">HackerOne</h2>
          <p className="text-sm text-gray-400 flex-1">Sync bug bounty programs and targets automatically.</p>
          <button className="px-4 py-2 bg-white/10 hover:bg-white/20 text-white rounded transition">
            Sync Now
          </button>
        </div>

        {/* Bugcrowd */}
        <div className="glass-panel p-6 border border-white/10 rounded-xl flex flex-col space-y-4">
          <h2 className="text-lg font-medium text-white">Bugcrowd</h2>
          <p className="text-sm text-gray-400 flex-1">Integrate Bugcrowd scope.</p>
          <button className="px-4 py-2 bg-white/10 hover:bg-white/20 text-white rounded transition">
            Sync Now
          </button>
        </div>

        {/* Intigriti */}
        <div className="glass-panel p-6 border border-white/10 rounded-xl flex flex-col space-y-4">
          <h2 className="text-lg font-medium text-white">Intigriti</h2>
          <p className="text-sm text-gray-400 flex-1">Coming soon.</p>
          <button className="px-4 py-2 bg-white/5 text-gray-500 rounded cursor-not-allowed" disabled>
            Not Configured
          </button>
        </div>
      </div>
    </div>
  );
};

export default IntegrationsPage;
