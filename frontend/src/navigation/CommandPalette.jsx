import React, { useEffect, useState, useRef } from 'react';
import { useNavigate } from 'react-router-dom';

const CommandPalette = ({ onClose }) => {
  const [query, setQuery] = useState('');
  const navigate = useNavigate();
  const inputRef = useRef(null);

  useEffect(() => {
    inputRef.current?.focus();
    
    const handleEscape = (e) => {
      if (e.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', handleEscape);
    return () => window.removeEventListener('keydown', handleEscape);
  }, [onClose]);

  const actions = [
    { id: '1', title: 'Start New Hunt', icon: 'M13 10V3L4 14h7v7l9-11h-7z', action: () => { navigate('/app/hunts'); onClose(); } },
    { id: '2', title: 'View Critical Findings', icon: 'M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z', action: () => { navigate('/app/findings'); onClose(); } },
    { id: '3', title: 'Ask AI Copilot', icon: 'M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z', action: () => { navigate('/app/chat'); onClose(); } },
    { id: '4', title: 'Generate Report', icon: 'M9 17v-2m3 2v-4m3 4v-6m2 10H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z', action: () => { navigate('/app/reports'); onClose(); } },
  ];

  const filtered = query === '' 
    ? actions 
    : actions.filter(a => a.title.toLowerCase().includes(query.toLowerCase()));

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center pt-32 bg-black/50 backdrop-blur-sm" onClick={onClose}>
      <div 
        className="w-full max-w-2xl bg-[#13192B] rounded-xl border border-white/10 shadow-2xl overflow-hidden"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center px-4 py-3 border-b border-white/10">
          <svg className="w-5 h-5 text-cyan-400 mr-3" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" /></svg>
          <input 
            ref={inputRef}
            type="text" 
            placeholder="Search commands, targets, or ask AI..."
            className="flex-1 bg-transparent border-none text-gray-200 placeholder-gray-500 focus:outline-none focus:ring-0 text-lg"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
          />
          <span className="text-xs font-mono text-gray-500 bg-white/5 px-2 py-1 rounded">ESC</span>
        </div>
        
        <div className="max-h-96 overflow-y-auto py-2 custom-scrollbar">
          {filtered.length > 0 ? (
            <div className="px-2 space-y-1">
              <div className="px-3 py-1 text-xs font-semibold text-gray-500 uppercase tracking-wider">Quick Actions</div>
              {filtered.map(action => (
                <button 
                  key={action.id}
                  onClick={action.action}
                  className="w-full flex items-center px-3 py-3 rounded-lg hover:bg-cyan-500/10 text-gray-300 hover:text-cyan-400 transition-colors group text-left"
                >
                  <svg className="w-5 h-5 mr-3 text-gray-500 group-hover:text-cyan-400 transition-colors" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.5" d={action.icon} />
                  </svg>
                  <span className="font-medium">{action.title}</span>
                </button>
              ))}
            </div>
          ) : (
            <div className="py-8 text-center text-gray-500">
              No results found for "{query}"
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default CommandPalette;
