import { api } from './api'

export interface AuditLogItem {
  id: string
  user_id: string | null
  user_email: string | null
  action: string
  detail: Record<string, unknown>
  ip_address: string | null
  timestamp: string
}

export interface AuditListParams {
  user_id?: string
  action?: string
  target_type?: string
  target_id?: string
  date_from?: string
  date_to?: string
  page?: number
  page_size?: number
}

export interface AuditListResponse {
  results: AuditLogItem[]
  count: number
}

export function getAuditLog(params?: AuditListParams): Promise<AuditListResponse> {
  return api.get<AuditListResponse>('/api/audit/', { params }).then((r) => r.data)
}

export function getDocumentActivity(docId: string): Promise<AuditLogItem[]> {
  return api.get<AuditLogItem[]>(`/api/audit/document/${docId}/`).then((r) => r.data)
}
