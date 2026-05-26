import api from '../client'

export interface Checkpoint {
  id: string
  title: string
  description: string
  required: boolean
  expected_findings?: string
  evidence_needed: string[]
}

export interface VerificationStep {
  step_number: number
  title: string
  description: string
  action: string
  payload?: string
  inject_where?: string
  expected_if_real?: string
  expected_if_false_positive?: string
}

export interface VerificationWorkflow {
  workflow_id: string
  finding_id: string
  status: string
  vulnerability_type: string
  organization_id: string
  checkpoints_total: number
  checkpoints: Checkpoint[]
  verification_steps: VerificationStep[]
  completeness: string
}

export async function getVerificationWizard(findingId: string): Promise<VerificationWorkflow> {
  const r = await api.get(`/sensei/verify/${findingId}`)
  return r.data as VerificationWorkflow
}
