import React from 'react';

const Navbar: React.FC = () => {
  return (
    <header className="h-20 glass-panel border-b border-white/10 flex items-center justify-between px-8 z-10 sticky top-0">
      <div className="flex items-center flex-1">
        <div className="relative w-96">
          <span className="absolute inset-y-0 left-0 flex items-center pl-3 text-gray-400">
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
            </svg>
          </span>
          <input
            type="text"
            className="w-full bg-background-card/50 border border-white/10 rounded-full py-2 pl-10 pr-4 text-sm text-white placeholder-gray-500 focus:outline-none focus:ring-1 focus:ring-primary/50 focus:border-primary/50 transition-all shadow-[inset_0_0_10px_rgba(0,0,0,0.5)]"
            placeholder="Search assets, findings, or enter command..."
          />
        </div>
      </div>

      <div className="flex items-center space-x-6">
        <button className="relative text-gray-400 hover:text-white transition-colors">
          <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.5" d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9" />
          </svg>
          <span className="absolute top-0 right-0 w-2 h-2 bg-secondary rounded-full shadow-[0_0_8px_rgba(157,77,255,0.8)]"></span>
        </button>

        <div className="flex items-center space-x-3 pl-6 border-l border-white/10 cursor-pointer group">
          <div className="w-9 h-9 rounded-full bg-gradient-to-tr from-primary to-secondary p-[2px]">
            <div className="w-full h-full rounded-full bg-background flex items-center justify-center">
              <span className="text-sm font-bold text-white">OP</span>
            </div>
          </div>
          <div className="flex flex-col">
            <span className="text-sm font-semibold text-white group-hover:text-primary transition-colors">Operator 1</span>
            <span className="text-xs text-gray-400">Admin</span>
          </div>
        </div>
      </div>
    </header>
  );
};

export default Navbar;
