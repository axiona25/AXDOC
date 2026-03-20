import { api } from './api'

export interface DashboardStats {
  my_documents?: { total: number; draft: number; in_review: number; approved: number; rejected: number; archived: number }
  my_pending_steps?: number
  unread_notifications?: number
  recent_activity?: { id: string; user_id: string | null; user_email: string | null; action: string; detail: Record<string, unknown>; timestamp: string }[]
  total_users?: number
  total_documents?: number
  total_dossiers?: { open: number; archived: number }
  total_protocols?: { count: number; this_month: number }
  documents_by_status?: Record<string, number>
  active_workflows?: number
  storage_used_mb?: number
  pending_approvals?: number
  dossiers_responsible?: number
}

export interface RecentDocumentItem {
  id: string
  title: string
  status: string
  updated_at: string
  created_by_id: string | null
  created_by_email: string | null
  folder_name: string | null
}

export interface MyTaskItem {
  step_instance_id: string
  workflow_instance_id: string
  document_id: string
  document_title: string
  step_name: string
  step_action: string
  status: string
  deadline: string | null
  started_at: string | null
}

export function getDashboardStats(): Promise<DashboardStats> {
  return api.get('/api/dashboard/stats/').then((r) => r.data)
}

export function getRecentDocuments(): Promise<{ results: RecentDocumentItem[] }> {
  return api.get('/api/dashboard/recent_documents/').then((r) => r.data)
}

export function getMyTasks(): Promise<{ results: MyTaskItem[] }> {
  return api.get('/api/dashboard/my_tasks/').then((r) => r.data)
}
