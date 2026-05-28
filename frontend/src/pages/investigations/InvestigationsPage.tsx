import React from 'react'
import useAuthStore from '../../state/auth'
import InvestigationWorkspace from '../../collaboration/InvestigationWorkspace'

export const InvestigationsPage: React.FC = () => {
  const { activeOrgId } = useAuthStore()

  return (
    <div className="space-y-6">
      <InvestigationWorkspace organizationId={activeOrgId} />
    </div>
  )
}

export default InvestigationsPage
