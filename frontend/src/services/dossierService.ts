import { api } from './api'

export interface DossierItem {
  id: string
  title: string
  identifier: string
  status: string
  responsible: string | null
  responsible_email: string | null
  created_at: string
  updated_at: string
  document_count: number
  protocol_count: number
}

export interface DossierDocumentEntry {
  id: number
  document: string
  document_id: string
  document_title: string | null
  added_at: string
  notes: string
}

export interface DossierProtocolEntry {
  id: number
  protocol: string
  protocol_id: string
  protocol_display: string | null
  added_at: string
}

export interface DossierFolderEntry {
  id: number
  folder: string
  folder_name: string | null
  added_by: string | null
  added_at: string
}

export interface DossierEmailEntry {
  id: number
  email_type: string
  from_address: string
  to_addresses: string[]
  subject: string
  body: string
  received_at: string
  message_id: string
  added_at: string
}

export interface DossierFileEntry {
  id: number
  file: string
  file_name: string
  file_size: number
  file_type: string
  checksum: string
  uploaded_at: string
  notes: string
}

export interface DossierDetailItem extends DossierItem {
  description: string
  created_by: string | null
  archived_at: string | null
  metadata_structure?: string | { id: string; name?: string } | null
  metadata_values?: Record<string, unknown>
  documents: DossierDocumentEntry[]
  protocols: DossierProtocolEntry[]
  dossier_folders?: DossierFolderEntry[]
  dossier_emails?: DossierEmailEntry[]
  dossier_files?: DossierFileEntry[]
  allowed_user_ids: string[]
  allowed_ou_ids: string[]
  organizational_unit?: string | null
  organizational_unit_code?: string | null
  classification_code?: string
  classification_label?: string
  retention_years?: number
  retention_basis?: string
  archive_stage?: string
  closed_at?: string | null
  closed_by?: string | null
  index_generated_at?: string | null
  index_file?: string | null
}

export interface DossiersParams {
  filter?: 'mine' | 'all'
  status?: string
  page?: number
  responsible_id?: string
  ou_id?: string
}

export interface DossiersResponse {
  results: DossierItem[]
  count: number
  next: string | null
  previous: string | null
}

export function getDossiers(params?: DossiersParams): Promise<DossiersResponse> {
  return api.get<DossiersResponse>('/api/dossiers/', { params }).then((r) => r.data)
}

export function getDossier(id: string): Promise<DossierDetailItem> {
  return api.get<DossierDetailItem>(`/api/dossiers/${id}/`).then((r) => r.data)
}

/** Dettaglio completo con cartelle, email, file (FASE 22) */
export function getDossierDetail(id: string): Promise<DossierDetailItem> {
  return api.get<DossierDetailItem>(`/api/dossiers/${id}/detail_full/`).then((r) => r.data)
}

export interface CreateDossierPayload {
  title: string
  identifier?: string
  description?: string
  responsible?: string
  organizational_unit?: string | null
  classification_code?: string
  classification_label?: string
  retention_years?: number
  retention_basis?: string
  allowed_users?: string[]
  allowed_ous?: string[]
  metadata_structure_id?: string | null
  metadata_values?: Record<string, unknown>
}

export function createDossier(payload: CreateDossierPayload): Promise<DossierDetailItem> {
  const body = { ...payload }
  if (body.metadata_values && Object.keys(body.metadata_values).length === 0) delete body.metadata_values
  if (body.metadata_structure_id == null) delete body.metadata_structure_id
  return api.post<DossierDetailItem>('/api/dossiers/', body).then((r) => r.data)
}

export function updateDossier(id: string, data: Partial<CreateDossierPayload>): Promise<DossierDetailItem> {
  return api.patch<DossierDetailItem>(`/api/dossiers/${id}/`, data).then((r) => r.data)
}

export function deleteDossier(id: string): Promise<void> {
  return api.delete(`/api/dossiers/${id}/`).then(() => undefined)
}

export function archiveDossier(id: string): Promise<DossierDetailItem> {
  return api.post<DossierDetailItem>(`/api/dossiers/${id}/archive/`).then((r) => r.data)
}

export function addDossierDocument(dossierId: string, documentId: string, notes?: string): Promise<DossierDetailItem> {
  return api.post<DossierDetailItem>(`/api/dossiers/${dossierId}/add_document/`, { document_id: documentId, notes }).then((r) => r.data)
}

export function removeDossierDocument(dossierId: string, documentId: string): Promise<DossierDetailItem> {
  return api.delete<DossierDetailItem>(`/api/dossiers/${dossierId}/remove_document/${documentId}/`).then((r) => r.data)
}

export function addDossierProtocol(dossierId: string, protocolId: string): Promise<DossierDetailItem> {
  return api.post<DossierDetailItem>(`/api/dossiers/${dossierId}/add_protocol/`, { protocol_id: protocolId }).then((r) => r.data)
}

export function removeDossierProtocol(dossierId: string, protocolId: string): Promise<DossierDetailItem> {
  return api.delete<DossierDetailItem>(`/api/dossiers/${dossierId}/remove_protocol/${protocolId}/`).then((r) => r.data)
}

export function getDossierDocuments(dossierId: string): Promise<DossierDocumentEntry[]> {
  return api.get<DossierDocumentEntry[]>(`/api/dossiers/${dossierId}/documents/`).then((r) => r.data)
}

export function getDossierProtocols(dossierId: string): Promise<DossierProtocolEntry[]> {
  return api.get<DossierProtocolEntry[]>(`/api/dossiers/${dossierId}/protocols/`).then((r) => r.data)
}

export function addDossierFolder(dossierId: string, folderId: string): Promise<DossierDetailItem> {
  return api.post<DossierDetailItem>(`/api/dossiers/${dossierId}/add_folder/`, { folder_id: folderId }).then((r) => r.data)
}

export function removeDossierFolder(dossierId: string, dossierFolderId: string): Promise<DossierDetailItem> {
  return api.post<DossierDetailItem>(`/api/dossiers/${dossierId}/remove_folder/`, { dossier_folder_id: dossierFolderId }).then((r) => r.data)
}

export interface AddDossierEmailPayload {
  email_type: 'pec' | 'email' | 'peo'
  from_address: string
  to_addresses?: string[]
  subject: string
  body?: string
  received_at?: string
  message_id?: string
}

export function addDossierEmail(dossierId: string, data: AddDossierEmailPayload): Promise<DossierEmailEntry> {
  return api.post<DossierEmailEntry>(`/api/dossiers/${dossierId}/add_email/`, data).then((r) => r.data)
}

export function uploadDossierFile(dossierId: string, file: File, notes?: string): Promise<DossierFileEntry> {
  const form = new FormData()
  form.append('file', file)
  if (notes) form.append('notes', notes)
  return api.post<DossierFileEntry>(`/api/dossiers/${dossierId}/upload_file/`, form, {
    headers: { 'Content-Type': 'multipart/form-data' },
  }).then((r) => r.data)
}

export function closeDossier(id: string): Promise<DossierDetailItem> {
  return api.post<DossierDetailItem>(`/api/dossiers/${id}/close/`).then((r) => r.data)
}

/** Genera indice PDF e ritorna blob; salva anche in dossier.index_file */
export function generateDossierIndex(id: string): Promise<Blob> {
  return api.get(`/api/dossiers/${id}/generate_index/`, { responseType: 'blob' }).then((r) => r.data as Blob)
}

export function getDossierAgidMetadata(id: string): Promise<Record<string, string | number>> {
  return api.get<Record<string, string | number>>(`/api/dossiers/${id}/agid_metadata/`).then((r) => r.data)
}
