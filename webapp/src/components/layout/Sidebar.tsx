import React from 'react';
import { NavLink, useLocation, useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import useAuthStore from '../../stores/authStore';

const navItems = [
  {
    path: '/app',
    label: 'Dashboard',
    exact: true,
    icon: 'M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6',
  },
  {
    path: '/app/organizations',
    label: 'Organizations',
    exact: false,
    icon: 'M12 6V4m6 2a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4m0 0a2 2 0 10-4 0m4 0a2 2 0 11-4 0m0 0V4m0 2a2 2 0 100 4m0-4a2 2 0 110 4m0 0v2m0 0a2 2 0 10-4 0m4 0a2 2 0 11-4 0m0 0v-2',
  },
  {
    path: '/app/recon',
    label: 'Recon Workspace',
    exact: false,
    icon: 'M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z',
  },
  {
    path: '/app/ai-recon',
    label: 'AI Recon Plan',
    exact: false,
    icon: 'M13 10V3L4 14h7v7l9-11h-7z',
  },
  {
    path: '/app/findings',
    label: 'Findings',
    exact: false,
    icon: 'M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z',
  },
  {
    path: '/app/assets',
    label: 'Asset Intelligence',
    exact: false,
    icon: 'M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10',
  },
  {
    path: '/app/copilot',
    label: 'AI Copilot',
    exact: false,
    icon: 'M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z',
  },
  {
    path: '/app/integrations',
    label: 'Integrations',
    exact: false,
    icon: 'M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1',
  },
];

const Sidebar: React.FC = () => {
  const location = useLocation();
  const navigate = useNavigate();
  const { user, clear } = useAuthStore();

  const handleLogout = () => {
    clear();
    navigate('/login');
  };

  return (
    <aside className="w-64 h-screen border-r border-white/10 glass-panel flex flex-col z-20 shrink-0">
      {/* Logo */}
      <div className="h-20 flex items-center px-6 border-b border-white/10 shrink-0">
        <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-primary to-secondary flex items-center justify-center mr-3 shadow-[0_0_15px_rgba(0,184,255,0.4)] shrink-0">
          <svg className="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.5" d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
          </svg>
        </div>
        <div>
          <span className="font-bold text-base tracking-wider text-gradient">NisargHunter</span>
          <div className="text-[10px] text-gray-500 font-mono">AI Recon v18</div>
        </div>
      </div>

      {/* Nav */}
      <nav className="flex-1 py-5 px-3 space-y-1 overflow-y-auto">
        <div className="px-3 mb-2">
          <span className="text-[10px] font-bold text-gray-600 uppercase tracking-widest">Navigation</span>
        </div>
        {navItems.map((item) => {
          const isActive = item.exact
            ? location.pathname === item.path
            : location.pathname.startsWith(item.path);
          return (
            <NavLink
              key={item.path}
              to={item.path}
              className={`relative flex items-center px-3 py-2.5 rounded-lg transition-all duration-300 ${
                isActive ? 'text-white' : 'text-gray-400 hover:text-white hover:bg-white/5'
              }`}
            >
              {isActive && (
                <motion.div
                  layoutId="activeTab"
                  className="absolute inset-0 bg-gradient-to-r from-primary/20 to-secondary/20 border border-primary/30 rounded-lg shadow-[0_0_15px_rgba(0,184,255,0.15)]"
                  initial={false}
                  transition={{ type: 'spring', stiffness: 400, damping: 30 }}
                />
              )}
              <svg className="w-4.5 h-4.5 mr-3 relative z-10 shrink-0" style={{width:'18px',height:'18px'}} fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={isActive ? 2 : 1.5} d={item.icon} />
              </svg>
              <span className={`relative z-10 font-medium text-sm ${isActive ? 'glow-primary' : ''}`}>
                {item.label}
              </span>
              {item.path === '/app/ai-recon' && (
                <span className="relative z-10 ml-auto text-[9px] font-bold bg-secondary/20 text-secondary border border-secondary/30 rounded px-1 py-0.5">AI</span>
              )}
            </NavLink>
          );
        })}
      </nav>

      {/* Bottom: user + status + logout */}
      <div className="p-3 border-t border-white/10 space-y-2 shrink-0">
        {user && (
          <div className="flex items-center space-x-2 px-2 py-2 rounded-lg bg-white/5">
            <div className="w-7 h-7 rounded-full bg-gradient-to-br from-primary to-secondary flex items-center justify-center text-xs font-bold text-white shrink-0">
              {user.username?.[0]?.toUpperCase() ?? 'U'}
            </div>
            <div className="flex-1 min-w-0">
              <div className="text-xs font-medium text-white truncate">{user.username}</div>
              <div className="text-[10px] text-gray-500 truncate">{user.role ?? 'Operator'}</div>
            </div>
          </div>
        )}
        <div className="flex items-center justify-between px-2">
          <div className="flex items-center space-x-2">
            <div className="w-2 h-2 rounded-full bg-green-400 shadow-[0_0_8px_rgba(74,222,128,0.8)] animate-pulse"></div>
            <span className="text-xs text-gray-400">System Online</span>
          </div>
          <button
            onClick={handleLogout}
            className="text-gray-500 hover:text-red-400 transition-colors p-1 rounded"
            title="Logout"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.5" d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" />
            </svg>
          </button>
        </div>
      </div>
    </aside>
  );
};

export default Sidebar;
