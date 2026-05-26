import React, { useState } from 'react';
import { Outlet } from 'react-router-dom';
import Sidebar from '../navigation/Sidebar';
import Topbar from '../navigation/Topbar';
import CommandPalette from '../navigation/CommandPalette';
import { WebSocketProvider } from '../providers/WebSocketProvider';

const MainLayout = () => {
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [commandPaletteOpen, setCommandPaletteOpen] = useState(false);

  // Toggle command palette with Cmd+K
  React.useEffect(() => {
    const handleKeyDown = (e) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault();
        setCommandPaletteOpen(true);
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  return (
    <WebSocketProvider>
      <div className="flex h-screen bg-[#0B0F19] text-gray-100 overflow-hidden font-sans">
        
        {/* Sidebar */}
        <Sidebar isOpen={sidebarOpen} setIsOpen={setSidebarOpen} />
        
        {/* Main Content Area */}
        <div className="flex-1 flex flex-col min-w-0 overflow-hidden relative">
          
          {/* Topbar */}
          <Topbar 
            toggleSidebar={() => setSidebarOpen(!sidebarOpen)} 
            openCommandPalette={() => setCommandPaletteOpen(true)} 
          />
          
          {/* Page Content */}
          <main className="flex-1 overflow-y-auto overflow-x-hidden p-6 bg-[#0B0F19]">
            <div className="max-w-7xl mx-auto">
              <Outlet />
            </div>
          </main>
          
        </div>
        
        {/* Command Palette Overlay */}
        {commandPaletteOpen && (
          <CommandPalette onClose={() => setCommandPaletteOpen(false)} />
        )}
      </div>
    </WebSocketProvider>
  );
};

export default MainLayout;
