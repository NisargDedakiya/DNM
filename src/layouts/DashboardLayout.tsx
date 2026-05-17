import React from "react";
import { NavLink, Outlet } from "react-router-dom";
import { useAuthStore } from "../stores/authStore";

export const DashboardLayout: React.FC = () => {
  const logout = useAuthStore((s) => s.logout);

  return (
    <div className="min-h-screen flex">
      <aside className="w-64 bg-gray-800 text-white p-4">
        <h2 className="text-xl font-bold mb-6">NisargHunter</h2>
        <nav className="flex flex-col gap-2">
          <NavLink to="/dashboard" className={({isActive}) => isActive ? 'font-semibold' : ''}>Dashboard</NavLink>
          <NavLink to="/programs" className={({isActive}) => isActive ? 'font-semibold' : ''}>Programs</NavLink>
          <NavLink to="/scans" className={({isActive}) => isActive ? 'font-semibold' : ''}>Scans</NavLink>
          <NavLink to="/findings" className={({isActive}) => isActive ? 'font-semibold' : ''}>Findings</NavLink>
        </nav>
      </aside>
      <div className="flex-1 bg-gray-100">
        <header className="flex justify-between items-center p-4 bg-white shadow">
          <div>Welcome</div>
          <div>
            <button onClick={logout} className="px-3 py-1 bg-red-500 text-white rounded">Logout</button>
          </div>
        </header>
        <main className="p-6">
          <Outlet />
        </main>
      </div>
    </div>
  );
};

export default DashboardLayout;
