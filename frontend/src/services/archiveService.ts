import { api } from './api'

export type ArchiveStage = 'current' | 'deposit' | 'historical'

export interface DocumentArchiveItem {
  id: number
  document: string
  document_title?: string
  stage: ArchiveStage
  stage_display?: string
  classification_code: string
  classification_label: string
  retention_years: number
  retention_rule: string
  archive_date?: string
  archive_by?: string
  historical_date?: string
  historical_by?: string
  discard_date?: string
  discard_approved: boolean
  conservation_package_id: string
  conservation_status: string
  conservation_response?: Record<string, unknown>
  notes?: string
  created_at: string
  updated_at: string
}

export interface RetentionRuleItem {
  id: number
  classification_code: string
  classification_label: string
  document_types: string[]
  retention_years: number
  retention_basis: string
  action_after_retention: string
  notes: string
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface InformationPackageItem {
  id: string
  package_type: 'PdV' | 'PdA' | 'PdD'
  package_id: string
  created_at: string
  created_by: string
  package_file?: string
  manifest_file?: string
  checksum: string
  signed_at?: string
  timestamp_token?: string
  status: string
  conservation_response?: Record<string, unknown>
  document_count: number
  protocol_count: number
  dossier_count: number
}

export interface TitolarioNode {
  code: string
  label: string
  children?: { code: string; label: string; retention?: number; action?: string; basis?: string; rule?: RetentionRuleItem }[]
}

export function getArchiveDocuments(stage: ArchiveStage, filters?: { ou?: string; classification?: string; type?: string; from?: string; to?: string }): Promise<DocumentArchiveItem[]> {
  const params: Record<string, string> = { stage }
  if (filters?.ou) params.ou = filters.ou
  if (filters?.classification) params.classification = filters.classification
  if (filters?.from) params.from = filters.from
  if (filters?.to) params.to = filters.to
  return api.get<{ results?: DocumentArchiveItem[] }>('/api/archive/documents/', { params }).then((r) => (Array.isArray(r.data) ? r.data : r.data?.results ?? []))
}

export function moveToDeposit(id: number, notes?: string): Promise<DocumentArchiveItem> {
  return api.post<DocumentArchiveItem>(`/api/archive/documents/${id}/move_to_deposit/`, { notes }).then((r) => r.data)
}

export function moveToHistorical(id: number, notes?: string): Promise<DocumentArchiveItem> {
  return api.post<DocumentArchiveItem>(`/api/archive/documents/${id}/move_to_historical/`, { notes }).then((r) => r.data)
}

export function requestDiscard(id: number): Promise<DocumentArchiveItem> {
  return api.post<DocumentArchiveItem>(`/api/archive/documents/${id}/request_discard/`).then((r) => r.data)
}

export function getPackages(filters?: { type?: string; status?: string }): Promise<InformationPackageItem[]> {
  const params = filters || {}
  return api.get<{ results?: InformationPackageItem[] }>('/api/archive/packages/', { params }).then((r) => (Array.isArray(r.data) ? r.data : r.data?.results ?? []))
}

export function createPdv(data: { document_ids: string[]; protocol_ids?: string[]; dossier_ids?: string[] }): Promise<InformationPackageItem> {
  return api.post<InformationPackageItem>('/api/archive/packages/create_pdv/', data).then((r) => r.data)
}

export function sendToConservator(id: string): Promise<InformationPackageItem> {
  return api.post<InformationPackageItem>(`/api/archive/packages/${id}/send_to_conservator/`).then((r) => r.data)
}

export function downloadPackage(id: string): Promise<Blob> {
  return api.get(`/api/archive/packages/${id}/download/`, { responseType: 'blob' }).then((r) => r.data)
}

export function generatePdd(id: string): Promise<Blob> {
  return api.get(`/api/archive/packages/${id}/generate_pdd/`, { responseType: 'blob' }).then((r) => r.data)
}

export function getRetentionRules(): Promise<RetentionRuleItem[]> {
  return api.get<{ results?: RetentionRuleItem[] }>('/api/archive/retention-rules/').then((r) => (Array.isArray(r.data) ? r.data : r.data?.results ?? []))
}

export function createRetentionRule(data: Partial<RetentionRuleItem>): Promise<RetentionRuleItem> {
  return api.post<RetentionRuleItem>('/api/archive/retention-rules/', data).then((r) => r.data)
}

export function updateRetentionRule(id: number, data: Partial<RetentionRuleItem>): Promise<RetentionRuleItem> {
  return api.patch<RetentionRuleItem>(`/api/archive/retention-rules/${id}/`, data).then((r) => r.data)
}

export function getTitolario(): Promise<TitolarioNode[]> {
  return api.get<TitolarioNode[]>('/api/archive/titolario/').then((r) => r.data)
}

export function getTitolarioByCode(code: string): Promise<RetentionRuleItem> {
  return api.get<RetentionRuleItem>(`/api/archive/titolario/${encodeURIComponent(code)}/`).then((r) => r.data)
}
