import React from 'react';

const HackerOnePage: React.FC = () => {
  const programs = [
    { id: 1, name: 'Yahoo', handle: 'yahoo', targets: 45, bounty: true },
    { id: 2, name: 'Uber', handle: 'uber', targets: 120, bounty: true },
    { id: 3, name: 'Shopify', handle: 'shopify', targets: 15, bounty: true }
  ];

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-white mb-2">HackerOne Programs</h1>
        <p className="text-gray-400">Select a program to view details and set as target.</p>
      </div>
      
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {programs.map((prog) => (
          <div key={prog.id} className="glass-panel p-6 border border-white/5 hover:border-primary/50 transition-colors flex flex-col justify-between">
            <div>
              <h3 className="text-xl font-bold text-white mb-1">{prog.name}</h3>
              <p className="text-sm text-gray-400 mb-4">@{prog.handle}</p>
              <div className="flex justify-between text-sm text-gray-300 mb-6">
                <span>Targets: <strong className="text-white">{prog.targets}</strong></span>
                <span>Bounty: <strong className="text-green-400">Yes</strong></span>
              </div>
            </div>
            <button className="w-full py-2 bg-white/5 hover:bg-primary/20 text-primary border border-primary/30 font-medium rounded-lg transition-all">
              Select Target
            </button>
          </div>
        ))}
      </div>
    </div>
  );
};

export default HackerOnePage;
