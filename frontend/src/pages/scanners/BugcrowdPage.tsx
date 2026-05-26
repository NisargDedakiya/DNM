import React, { useState } from 'react';

const BugcrowdPage: React.FC = () => {
  const [url, setUrl] = useState('');
  
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-white mb-2">Bugcrowd Scanner</h1>
        <p className="text-gray-400">Enter a target URL from a Bugcrowd program to initiate a scan.</p>
      </div>
      <div className="glass-panel p-6 border border-white/5 max-w-2xl">
        <label className="block text-sm font-medium text-gray-300 mb-2">Target URL</label>
        <div className="flex gap-4">
          <input 
            type="url" 
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            placeholder="https://example.com"
            className="flex-1 bg-white/5 border border-white/10 rounded-lg px-4 py-2 text-white focus:outline-none focus:border-primary/50 focus:ring-1 focus:ring-primary/50"
          />
          <button className="px-6 py-2 bg-gradient-to-r from-primary to-secondary text-white font-medium rounded-lg shadow-[0_0_15px_rgba(0,184,255,0.4)] hover:shadow-[0_0_25px_rgba(0,184,255,0.6)] transition-all">
            Initiate Scan
          </button>
        </div>
      </div>
    </div>
  );
};

export default BugcrowdPage;
