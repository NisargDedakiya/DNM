import React from 'react'
import { Navigate, useLocation } from 'react-router-dom'
import useAuthStore from '../state/auth'

interface ProtectedRouteProps {
  children: React.ReactNode
  requiredRole?: string
}

export const ProtectedRoute: React.FC<ProtectedRouteProps> = ({ children, requiredRole }) => {
  const { isAuthenticated, activeOrgId, user } = useAuthStore()
  const location = useLocation()

  if (!isAuthenticated) {
    return <Navigate to="/login" state={{ from: location }} replace />
  }

  if (!activeOrgId && location.pathname !== '/org-select') {
    return <Navigate to="/org-select" replace />
  }

  if (requiredRole && user?.role && user.role !== requiredRole && user.role !== 'owner' && user.role !== 'admin') {
    return <Navigate to="/app" replace />
  }

  return <>{children}</>
}

export default ProtectedRoute
