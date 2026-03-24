import { api } from './api'

// ─── Types ────────────────────────────────────────
export interface WorkflowStep {
  id: string
  template: string
  name: string
  order: number
  action: 'review' | 'approve' | 'sign' | 'acknowledge'
  assignee_type: 'role' | 'ou_role' | 'specific_user' | 'document_ou'
  assignee_role: string | null
  assignee_user: string | null
  assignee_ou: string | null
  assignee_ou_role: string | null
  is_required: boolean
  deadline_days: number | null
  instructions: string
  assignee_display: string
}

export interface WorkflowTemplate {
  id: string
  name: string
  description: string
  is_published: boolean
  created_by: string | null
  created_at: string
  updated_at: string
  step_count: number
  steps?: WorkflowStep[]
}

export interface WorkflowStepInstance {
  id: string
  step: string
  step_name: string
  step_action: string
  assigned_to: string[]
  assigned_to_emails: string[]
  status: string
  started_at: string | null
  completed_at: string | null
  completed_by: string | null
  action_taken: string | null
  comment: string
  deadline: string | null
}

export interface WorkflowInstance {
  id: string
  template: string
  template_name: string
  document: string
  document_title: string
  started_by: string | null
  started_at: string
  completed_at: string | null
  status: string
  current_step_order: number
  step_instances: WorkflowStepInstance[]
  current_step_instance: WorkflowStepInstance | null
}

// ─── Templates ────────────────────────────────────
export function getWorkflowTemplates(params?: { mine?: string }): Promise<{ results: WorkflowTemplate[]; count: number }> {
  return api.get('/api/workflows/templates/', { params }).then((r) => r.data)
}

export function getWorkflowTemplate(id: string): Promise<WorkflowTemplate> {
  return api.get(`/api/workflows/templates/${id}/`).then((r) => r.data)
}

export function createWorkflowTemplate(data: { name: string; description?: string }): Promise<WorkflowTemplate> {
  return api.post('/api/workflows/templates/', data).then((r) => r.data)
}

export function updateWorkflowTemplate(id: string, data: { name?: string; description?: string }): Promise<WorkflowTemplate> {
  return api.patch(`/api/workflows/templates/${id}/`, data).then((r) => r.data)
}

export function deleteWorkflowTemplate(id: string): Promise<void> {
  return api.delete(`/api/workflows/templates/${id}/`)
}

export function publishWorkflow(id: string): Promise<WorkflowTemplate> {
  return api.post(`/api/workflows/templates/${id}/publish/`).then((r) => r.data)
}

export function unpublishWorkflow(id: string): Promise<WorkflowTemplate> {
  return api.post(`/api/workflows/templates/${id}/unpublish/`).then((r) => r.data)
}

// ─── Steps ────────────────────────────────────────
export function getWorkflowSteps(templateId: string): Promise<WorkflowStep[]> {
  return api.get(`/api/workflows/templates/${templateId}/steps/`).then((r) => r.data)
}

export function createWorkflowStep(templateId: string, data: Partial<WorkflowStep>): Promise<WorkflowStep> {
  return api.post(`/api/workflows/templates/${templateId}/steps/`, data).then((r) => r.data)
}

export function updateWorkflowStep(templateId: string, stepId: string, data: Partial<WorkflowStep>): Promise<WorkflowStep> {
  return api.patch(`/api/workflows/templates/${templateId}/steps/${stepId}/`, data).then((r) => r.data)
}

export function deleteWorkflowStep(templateId: string, stepId: string): Promise<void> {
  return api.delete(`/api/workflows/templates/${templateId}/steps/${stepId}/`)
}

// ─── Instances ────────────────────────────────────
export function getWorkflowInstances(params?: { document_id?: string; status?: string; template_id?: string }): Promise<{ results: WorkflowInstance[]; count: number }> {
  return api.get('/api/workflows/instances/', { params }).then((r) => r.data)
}

export function getWorkflowInstance(id: string): Promise<WorkflowInstance> {
  return api.get(`/api/workflows/instances/${id}/`).then((r) => r.data)
}

// ─── Start / Action / Cancel ──────────────────────
export function startWorkflow(data: { template: string; document: string }): Promise<WorkflowInstance> {
  return api.post('/api/workflows/instances/', data).then((r) => r.data)
}

export function performStepAction(
  instanceId: string,
  data: { action: 'approve' | 'reject' | 'complete'; comment?: string },
): Promise<WorkflowInstance> {
  return api.post(`/api/workflows/instances/${instanceId}/action/`, data).then((r) => r.data)
}

export function cancelWorkflow(instanceId: string): Promise<WorkflowInstance> {
  return api.post(`/api/workflows/instances/${instanceId}/cancel/`).then((r) => r.data)
}

export function getPublishedTemplates(): Promise<{ results: WorkflowTemplate[]; count: number }> {
  return api.get('/api/workflows/templates/', { params: { is_published: true } }).then((r) => r.data)
}
