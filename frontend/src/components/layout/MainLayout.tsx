import React from 'react';
import { Outlet } from 'react-router-dom';
import Sidebar from './Sidebar';
import Navbar from './Navbar';

const MainLayout: React.FC = () => {
  return (
    <div className="flex h-screen bg-background overflow-hidden selection:bg-primary/30">
      {/* Background Cyber Grid */}
      <div className="fixed inset-0 z-0 opacity-[0.03] pointer-events-none" 
           style={{ backgroundImage: 'linear-gradient(#00B8FF 1px, transparent 1px), linear-gradient(90deg, #00B8FF 1px, transparent 1px)', backgroundSize: '40px 40px' }}>
      </div>
      
      {/* Animated glow orbs */}
      <div className="fixed top-[-10%] left-[-10%] w-[40%] h-[40%] rounded-full bg-primary/10 blur-[120px] pointer-events-none animate-pulse-glow z-0"></div>
      <div className="fixed bottom-[-10%] right-[-10%] w-[40%] h-[40%] rounded-full bg-secondary/10 blur-[120px] pointer-events-none animate-pulse-glow z-0" style={{ animationDelay: '1s' }}></div>

      <Sidebar />
      <div className="flex-1 flex flex-col relative z-10 overflow-hidden">
        <Navbar />
        <main className="flex-1 overflow-y-auto p-6 scroll-smooth">
          <Outlet />
        </main>
      </div>
    </div>
  );
};

export default MainLayout;
