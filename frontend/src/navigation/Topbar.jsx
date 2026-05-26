import React from 'react';
import useRealtimeStore from '../store/useRealtimeStore';

const Topbar = ({ toggleSidebar, openCommandPalette }) => {
  const isConnected = useRealtimeStore((s) => s.isConnected);

  return (
    <header className="h-16 bg-[#0B0F19]/80 backdrop-blur-md border-b border-white/5 flex items-center justify-between px-4 z-10 sticky top-0">
      
      {/* Left side */}
      <div className="flex items-center space-x-4">
        <button onClick={toggleSidebar} className="text-gray-400 hover:text-white focus:outline-none transition-colors">
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M4 6h16M4 12h16M4 18h7" />
          </svg>
        </button>
        
        {/* Command Palette Trigger */}
        <button 
          onClick={openCommandPalette}
          className="hidden sm:flex items-center px-3 py-1.5 bg-[#13192B] border border-white/10 rounded-md text-sm text-gray-400 hover:bg-[#1A2235] hover:text-gray-200 transition-colors w-64 justify-between group"
        >
          <span className="flex items-center space-x-2">
            <svg className="w-4 h-4 text-gray-500 group-hover:text-cyan-400 transition-colors" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" /></svg>
            <span>Search workspace...</span>
          </span>
          <span className="text-xs bg-white/5 px-1.5 py-0.5 rounded border border-white/10">⌘K</span>
        </button>
      </div>
      
      {/* Right side */}
      <div className="flex items-center space-x-5">
        
        {/* Realtime Status */}
        <div className="flex items-center space-x-2">
          <div className="relative flex items-center justify-center">
            {isConnected && <span className="absolute inline-flex h-full w-full rounded-full bg-cyan-400 opacity-20 animate-ping"></span>}
            <span className={`relative inline-flex rounded-full h-2 w-2 ${isConnected ? 'bg-cyan-400 shadow-[0_0_8px_rgba(34,211,238,0.8)]' : 'bg-red-500'}`}></span>
          </div>
          <span className="text-xs font-medium text-gray-400 tracking-wide uppercase hidden sm:block">
            {isConnected ? 'Live Sync' : 'Disconnected'}
          </span>
        </div>

        {/* Notifications */}
        <button className="relative text-gray-400 hover:text-white transition-colors">
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.5" d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9" /></svg>
        </button>
        
        {/* Profile */}
        <div className="w-8 h-8 rounded-full bg-[#1A2235] border border-white/10 flex items-center justify-center cursor-pointer hover:border-cyan-500/50 transition-colors">
          <span className="text-sm font-medium text-gray-200">OP</span>
        </div>
      </div>
      
    </header>
  );
};

export default Topbar;
