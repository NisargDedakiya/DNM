import React from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import LandingPage from './pages/landing/LandingPage';
import LoginPage from './pages/auth/LoginPage';
import Dashboard from './pages/dashboard/Dashboard';
import CopilotPage from './pages/copilot/CopilotPage';
import SenseiAIPage from './pages/sensei/SenseiAIPage';
import TasksPage from './pages/tasks/TasksPage';
import GuidePage from './pages/guide/GuidePage';
import BugcrowdPage from './pages/scanners/BugcrowdPage';
import HackerOnePage from './pages/scanners/HackerOnePage';
import ReportsPage from './pages/reports/ReportsPage';
import MainLayout from './components/layout/MainLayout';
import useAuthStore from './stores/authStore';
import ExposureGridView from './grid/ExposureGridView';


// Auth guard — redirects unauthenticated users to /login
const ProtectedRoute: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { isAuthenticated } = useAuthStore();
  if (!isAuthenticated) return <Navigate to="/login" replace />;
  return <>{children}</>;
};

const AppRoutes: React.FC = () => {
  const { isAuthenticated } = useAuthStore();
  return (
    <Routes>
      <Route path="/" element={<LandingPage />} />
      <Route path="/login" element={
        isAuthenticated ? <Navigate to="/app" replace /> : <LoginPage />
      } />
      
      {/* Protected Dashboard Routes */}
      <Route path="/app" element={
        <ProtectedRoute>
          <MainLayout />
        </ProtectedRoute>
      }>
        <Route index element={<Dashboard />} />
        <Route path="ai-copilot" element={<CopilotPage />} />
        <Route path="sensei-ai" element={<SenseiAIPage />} />
        <Route path="tasks" element={<TasksPage />} />
        <Route path="manual-guide" element={<GuidePage />} />
        <Route path="bugcrowd" element={<BugcrowdPage />} />
        <Route path="hackerone" element={<HackerOnePage />} />
        <Route path="reports" element={<ReportsPage />} />
        <Route path="exposure-grid" element={<ExposureGridView />} />
      </Route>
      
      {/* Fallback */}
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
};

export default AppRoutes;
