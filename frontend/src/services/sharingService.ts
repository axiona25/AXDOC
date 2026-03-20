import { api } from './api'

const baseURL = import.meta.env.VITE_API_URL || ''

export type ShareRecipientType = 'internal' | 'external'

export interface ShareLinkItem {
  id: string
  token: string
  target_type: 'document' | 'protocol'
  document: string | null
  protocol: string | null
  recipient_type: ShareRecipientType
  recipient_user: string | null
  recipient_email: string
  recipient_name: string
  recipient_display: string
  can_download: boolean
  password_protected: boolean
  expires_at: string | null
  max_accesses: number | null
  access_count: number
  is_active: boolean
  created_at: string
  last_accessed_at: string | null
  is_valid: boolean
  url: string
}

export interface CreateSharePayload {
  recipient_type: ShareRecipientType
  recipient_user_id?: string
  recipient_email?: string
  recipient_name?: string
  can_download?: boolean
  expires_in_days?: number | null
  max_accesses?: number | null
  password?: string | null
}

export interface CreateShareResponse {
  share_link_id: string
  token: string
  url: string
}

export interface PublicShareData {
  document: {
    id: string
    title: string
    description: string
    status: string
    current_version: number
  } | null
  shared_by: { name: string; email: string }
  can_download: boolean
  expires_at: string | null
  accesses_remaining: number | null
}

export function shareDocument(docId: string, data: CreateSharePayload): Promise<CreateShareResponse> {
  return api.post(`/api/documents/${docId}/share/`, data).then((r) => r.data)
}

export function shareProtocol(protoId: string, data: CreateSharePayload): Promise<CreateShareResponse> {
  return api.post(`/api/protocols/${protoId}/share/`, data).then((r) => r.data)
}

export function getDocumentShares(docId: string): Promise<ShareLinkItem[]> {
  return api.get(`/api/documents/${docId}/shares/`).then((r) => r.data)
}

export function getProtocolShares(protoId: string): Promise<ShareLinkItem[]> {
  return api.get(`/api/protocols/${protoId}/shares/`).then((r) => r.data)
}

export function revokeShare(shareId: string): Promise<ShareLinkItem> {
  return api.post(`/api/sharing/${shareId}/revoke/`).then((r) => r.data)
}

/** Accesso pubblico (senza login). */
export function getPublicShare(token: string): Promise<PublicShareData> {
  return api.get(`/api/public/share/${token}/`).then((r) => r.data)
}

export function verifySharePassword(token: string, password: string): Promise<{ valid: boolean; data?: PublicShareData }> {
  return api.post(`/api/public/share/${token}/verify_password/`, { password }).then((r) => r.data)
}

/** Download file via link pubblico (blob). */
export function downloadSharedFile(token: string, password?: string): Promise<Blob> {
  const url = `${baseURL}/api/public/share/${token}/download/`
  const headers: Record<string, string> = {}
  if (password) headers['X-Share-Password'] = password
  return fetch(url, { credentials: 'include', headers }).then((res) => {
    if (!res.ok) throw new Error(res.statusText)
    return res.blob()
  })
}
