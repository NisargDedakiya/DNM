import React from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import LandingPage from './pages/landing/LandingPage';
import LoginPage from './pages/auth/LoginPage';
import Dashboard from './pages/dashboard/Dashboard';
import ReconWorkspace from './pages/recon/ReconWorkspace';
import AIReconPage from './pages/recon/AIReconPage';
import FindingsPage from './pages/findings/FindingsPage';
import AssetsPage from './pages/assets/AssetsPage';
import CopilotPage from './pages/copilot/CopilotPage';
import IntegrationsPage from './pages/integrations/IntegrationsPage';
import OrganizationsPage from './pages/organizations/OrganizationsPage';
import MainLayout from './components/layout/MainLayout';
import useAuthStore from './stores/authStore';

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
        <Route path="recon" element={<ReconWorkspace />} />
        <Route path="ai-recon" element={<AIReconPage />} />
        <Route path="findings" element={<FindingsPage />} />
        <Route path="assets" element={<AssetsPage />} />
        <Route path="copilot" element={<CopilotPage />} />
        <Route path="integrations" element={<IntegrationsPage />} />
        <Route path="organizations" element={<OrganizationsPage />} />
      </Route>
      
      {/* Fallback */}
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
};

export default AppRoutes;
