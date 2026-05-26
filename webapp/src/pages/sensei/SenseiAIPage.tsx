import React from 'react';

const SenseiAIPage: React.FC = () => {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-white mb-2">Sensei AI</h1>
        <p className="text-gray-400">Advanced AI vulnerability analysis and exploitation guidance.</p>
      </div>
      <div className="glass-panel p-8 text-center border border-white/5">
        <h3 className="text-xl font-medium text-white mb-4">Sensei AI is currently processing threat models...</h3>
        <p className="text-gray-400">Enter a specific finding or target to begin deep analysis.</p>
      </div>
    </div>
  );
};

export default SenseiAIPage;
