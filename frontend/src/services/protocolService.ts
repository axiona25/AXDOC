import { api } from './api'

export interface ProtocolItem {
  id: string
  protocol_id: string
  segnatura?: string
  number: number | null
  year: number | null
  direction: string
  subject: string
  sender_receiver: string
  organizational_unit: string | null
  organizational_unit_name: string | null
  registered_at: string | null
  registered_by: string | null
  status: string
  document: string | null
  protocol_display?: string
  category?: string
}

export interface DailyRegisterResponse {
  date: string
  protocols: ProtocolItem[]
}

export interface ProtocolDetailItem extends ProtocolItem {
  notes: string
  document_title: string | null
  attachment_ids: string[]
  created_at: string
  category: string
  description: string
  dossier_ids: string[]
  document_file?: string | null
}

export interface ProtocolsParams {
  direction?: 'in' | 'out' | string
  ou_id?: string
  year?: number
  status?: string
  search?: string
  filter?: 'mine' | 'all'
  page?: number
  date_from?: string
  date_to?: string
}

export interface ProtocolsResponse {
  results: ProtocolItem[]
  count: number
  next: string | null
  previous: string | null
}

export function getProtocols(params?: ProtocolsParams): Promise<ProtocolsResponse> {
  return api.get<ProtocolsResponse>('/api/protocols/', { params }).then((r) => r.data)
}

/** Registro giornaliero: protocolli registrati in una data (YYYY-MM-DD). Segnatura AGID. */
export function getDailyRegister(date: string, ouId?: string): Promise<DailyRegisterResponse> {
  const params: { date: string; ou_id?: string } = { date }
  if (ouId) params.ou_id = ouId
  return api.get<DailyRegisterResponse>('/api/protocols/daily_register/', { params }).then((r) => r.data)
}

export function getProtocol(id: string): Promise<ProtocolDetailItem> {
  return api.get<ProtocolDetailItem>(`/api/protocols/${id}/`).then((r) => r.data)
}

export interface CreateProtocolPayload {
  direction: 'in' | 'out'
  subject: string
  description?: string
  category?: string
  sender_receiver?: string
  organizational_unit: string
  document?: string
  notes?: string
  attachment_ids?: string[]
  dossier_ids?: string[]
}

export function createProtocol(payload: CreateProtocolPayload): Promise<ProtocolDetailItem> {
  return api.post<ProtocolDetailItem>('/api/protocols/', payload).then((r) => r.data)
}

export function createProtocolWithFile(
  payload: CreateProtocolPayload,
  file?: File
): Promise<ProtocolDetailItem> {
  if (!file) {
    return api.post<ProtocolDetailItem>('/api/protocols/', payload).then((r) => r.data)
  }
  const form = new FormData()
  Object.entries(payload).forEach(([key, value]) => {
    if (value !== undefined && value !== null) {
      if (Array.isArray(value)) {
        value.forEach((v) => form.append(key, String(v)))
      } else {
        form.append(key, String(value))
      }
    }
  })
  form.append('file_upload', file)
  return api
    .post<ProtocolDetailItem>('/api/protocols/', form, {
      transformRequest: (data, headers) => {
        if (data instanceof FormData && headers && typeof (headers as { delete?: (k: string) => void }).delete === 'function') {
          ;(headers as { delete: (k: string) => void }).delete('Content-Type')
        }
        return data
      },
    })
    .then((r) => r.data)
}

export function updateProtocol(id: string, data: { subject?: string; sender_receiver?: string; notes?: string }): Promise<ProtocolDetailItem> {
  return api.patch<ProtocolDetailItem>(`/api/protocols/${id}/`, data).then((r) => r.data)
}

export function archiveProtocol(id: string): Promise<ProtocolDetailItem> {
  return api.post<ProtocolDetailItem>(`/api/protocols/${id}/archive/`).then((r) => r.data)
}

export function addProtocolAttachment(protocolId: string, documentId: string): Promise<ProtocolDetailItem> {
  return api.post<ProtocolDetailItem>(`/api/protocols/${protocolId}/add_attachment/`, { document_id: documentId }).then((r) => r.data)
}

/** Scarica il documento protocollato (richiede auth via api) */
export function downloadProtocolDocument(id: string, filename?: string): Promise<void> {
  return api
    .get(`/api/protocols/${id}/download/`, { responseType: 'blob' })
    .then((res) => {
      const blob = res.data as Blob
      const name = filename || `protocollo-${id}.pdf`
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = name
      a.click()
      URL.revokeObjectURL(url)
    })
}

export function getProtocolStampedUrl(id: string): string {
  const base = import.meta.env.VITE_API_URL || ''
  return `${base}/api/protocols/${id}/stamped_document/`
}

export function createProtocolFromDocument(documentId: string, payload: { organizational_unit_id: string; subject: string; sender_receiver?: string; notes?: string }): Promise<ProtocolDetailItem> {
  return api.post<ProtocolDetailItem>(`/api/documents/${documentId}/protocollo/`, payload).then((r) => r.data)
}
