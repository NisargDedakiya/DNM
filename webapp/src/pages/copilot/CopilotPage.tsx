import React, { useState } from 'react';

const CopilotPage: React.FC = () => {
  const [query, setQuery] = useState('');
  const [response, setResponse] = useState<any>(null);

  const handleQuery = async () => {
    // Basic stub, real app would call API
    setResponse({ message: `AI Copilot is processing: ${query}`, advisory: 'AI analysis is advisory only.' });
  };

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold tracking-wider text-gradient">AI Security Copilot</h1>
          <p className="text-gray-400 mt-1">Contextual investigation workspace</p>
        </div>
      </div>

      <div className="glass-panel p-6 border border-white/10 rounded-xl">
        <textarea 
          className="w-full bg-white/5 border border-white/10 rounded p-4 text-white focus:outline-none focus:border-primary"
          rows={4}
          placeholder="Ask a security question..."
          value={query}
          onChange={(e) => setQuery(e.target.value)}
        />
        <div className="mt-4 flex justify-end">
          <button 
            className="px-4 py-2 bg-primary hover:bg-primary/90 text-white font-medium rounded transition"
            onClick={handleQuery}
          >
            Ask Copilot
          </button>
        </div>
      </div>

      {response && (
        <div className="glass-panel p-6 border border-white/10 rounded-xl space-y-4">
          <div className="text-white">{response.message}</div>
          <div className="p-3 bg-yellow-500/10 border border-yellow-500/20 rounded-lg text-yellow-500 text-sm">
            {response.advisory}
          </div>
        </div>
      )}
    </div>
  );
};

export default CopilotPage;
