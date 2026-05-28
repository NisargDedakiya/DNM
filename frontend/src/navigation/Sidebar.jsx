import React from 'react';
import { NavLink } from 'react-router-dom';
import useRealtimeStore from '../store/useRealtimeStore';

const Sidebar = ({ isOpen, setIsOpen }) => {
  const activeAlerts = useRealtimeStore((state) => state.activeAlerts);
  const alertCount = activeAlerts.length;

  const navItems = [
    { name: 'Dashboard', path: '/app', icon: 'M4 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2V6zM14 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2V6zM4 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2v-2zM14 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2v-2z' },
    { name: 'Strategy Hunts', path: '/app/hunts', icon: 'M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z' },
    { name: 'Observability', path: '/app/observability', icon: 'M13 10V3L4 14h7v7l9-11h-7z' },
    { name: 'Findings', path: '/app/findings', icon: 'M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z', badge: alertCount },
    { name: 'Attack Graph', path: '/app/graph', icon: 'M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1' },
    { name: 'Reports', path: '/app/reports', icon: 'M9 17v-2m3 2v-4m3 4v-6m2 10H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z' },
    { name: 'AI Hunt Chat', path: '/app/chat', icon: 'M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z' },
    { name: 'Scheduler', path: '/app/scheduler', icon: 'M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z' },
  ];

  return (
    <div className={`flex flex-col bg-[#0F1423] border-r border-white/5 transition-all duration-300 ${isOpen ? 'w-64' : 'w-20'}`}>
      
      {/* Logo */}
      <div className="h-16 flex items-center px-4 border-b border-white/5">
        <div className="flex items-center space-x-3 overflow-hidden">
          <div className="w-8 h-8 rounded bg-gradient-to-tr from-cyan-500 to-blue-600 flex items-center justify-center flex-shrink-0 shadow-[0_0_15px_rgba(6,182,212,0.4)]">
            <span className="font-bold text-white text-lg leading-none">N</span>
          </div>
          {isOpen && <span className="font-bold text-white tracking-wide whitespace-nowrap">NisargHunter</span>}
        </div>
      </div>
      
      {/* Navigation */}
      <nav className="flex-1 py-4 overflow-y-auto custom-scrollbar">
        <div className="px-3 space-y-1">
          {navItems.map((item) => (
            <NavLink
              key={item.name}
              to={item.path}
              className={({ isActive }) => 
                `flex items-center px-3 py-2.5 rounded-lg transition-all duration-200 group ${
                  isActive 
                    ? 'bg-cyan-500/10 text-cyan-400' 
                    : 'text-gray-400 hover:bg-white/5 hover:text-gray-200'
                }`
              }
              title={!isOpen ? item.name : ''}
            >
              <svg className="w-5 h-5 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.5" d={item.icon} />
              </svg>
              
              {isOpen && (
                <div className="ml-3 flex-1 flex justify-between items-center whitespace-nowrap">
                  <span className="font-medium text-sm">{item.name}</span>
                  {item.badge > 0 && (
                    <span className="bg-red-500/20 text-red-400 text-xs font-bold px-2 py-0.5 rounded-full border border-red-500/30">
                      {item.badge}
                    </span>
                  )}
                </div>
              )}
              
              {/* Tooltip for collapsed state */}
              {!isOpen && item.badge > 0 && (
                 <div className="absolute top-1 right-1 w-2 h-2 rounded-full bg-red-500 shadow-[0_0_8px_rgba(239,68,68,0.8)]"></div>
              )}
            </NavLink>
          ))}
        </div>
      </nav>
      
      {/* Settings at Bottom */}
      <div className="p-4 border-t border-white/5">
        <NavLink to="/app/settings" className="flex items-center px-3 py-2 text-gray-400 hover:text-white rounded-lg hover:bg-white/5 transition-colors group">
          <svg className="w-5 h-5 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.5" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.5" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
          </svg>
          {isOpen && <span className="ml-3 font-medium text-sm whitespace-nowrap">Settings</span>}
        </NavLink>
      </div>
    </div>
  );
};

export default Sidebar;
