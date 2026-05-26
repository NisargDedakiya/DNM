import React from 'react';

const TasksPage: React.FC = () => {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-white mb-2">Pending Tasks</h1>
        <p className="text-gray-400">Manage your active reconnaissance and exploitation tasks.</p>
      </div>
      <div className="glass-panel p-6 border border-white/5">
        <div className="space-y-4">
          <div className="p-4 bg-white/5 rounded-lg border border-white/10 flex justify-between items-center">
            <div>
              <h4 className="text-white font-medium">Scan Bugcrowd Target</h4>
              <p className="text-sm text-gray-400">example.com - Scheduled</p>
            </div>
            <span className="px-3 py-1 bg-yellow-500/20 text-yellow-400 rounded text-xs font-medium border border-yellow-500/30">Pending</span>
          </div>
        </div>
      </div>
    </div>
  );
};

export default TasksPage;
