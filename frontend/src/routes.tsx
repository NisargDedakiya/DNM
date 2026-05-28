import React from 'react'
import { Routes, Route, Navigate } from 'react-router-dom'
import LandingPage from './pages/landing/LandingPage'
import LoginPage from './pages/auth/LoginPage'
import OrgSelectionPage from './pages/auth/OrgSelectionPage'
import Dashboard from './pages/dashboard/Dashboard'
import ProgramsPage from './pages/programs/ProgramsPage'
import FindingsWorkspacePage from './pages/findings/FindingsWorkspacePage'
import AttackGraphPage from './pages/graph/AttackGraphPage'
import InvestigationsPage from './pages/investigations/InvestigationsPage'
import ReportsPage from './pages/reports/ReportsPage'
import SenseiAIPage from './pages/sensei/SenseiAIPage'
import ExposureGridView from './grid/ExposureGridView'
import TasksPage from './pages/tasks/TasksPage'
import OrganizationsPage from './pages/organizations/OrganizationsPage'
import SchedulerPage from './pages/scheduler/SchedulerPage'
import MainLayout from './components/layout/MainLayout'
import ProtectedRoute from './routes/ProtectedRoute'

const AppRoutes: React.FC = () => {
  return (
    <Routes>
      <Route path="/" element={<LandingPage />} />
      <Route path="/login" element={<LoginPage />} />
      
      {/* Organization Selection Guard */}
      <Route path="/org-select" element={
        <ProtectedRoute>
          <OrgSelectionPage />
        </ProtectedRoute>
      } />

      {/* Protected Cyber Operations Layout */}
      <Route path="/app" element={
        <ProtectedRoute>
          <MainLayout />
        </ProtectedRoute>
      }>
        <Route index element={<Dashboard />} />
        <Route path="programs" element={<ProgramsPage />} />
        <Route path="monitoring" element={<SchedulerPage />} />
        <Route path="findings" element={<FindingsWorkspacePage />} />
        <Route path="graph" element={<AttackGraphPage />} />
        <Route path="investigations" element={<InvestigationsPage />} />
        <Route path="reports" element={<ReportsPage />} />
        <Route path="strategy" element={<SenseiAIPage />} />
        <Route path="threat-intelligence" element={<ExposureGridView />} />
        <Route path="marketplace" element={<TasksPage />} />
        <Route path="settings" element={<OrganizationsPage />} />
      </Route>
      
      {/* Fallback */}
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}

export default AppRoutes
