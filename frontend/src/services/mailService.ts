import { api } from './api'

// ─── Account ──────────────────────────────────
export interface MailAccount {
  id: string
  name: string
  account_type: 'email' | 'pec'
  email_address: string
  imap_host: string
  imap_port: number
  imap_use_ssl: boolean
  smtp_host: string
  smtp_port: number
  smtp_use_ssl: boolean
  smtp_use_tls: boolean
  is_active: boolean
  is_default: boolean
  last_fetch_at: string | null
  unread_count: number
  created_at: string
}

export interface CreateMailAccountPayload {
  name: string
  account_type: 'email' | 'pec'
  email_address: string
  imap_host: string
  imap_port: number
  imap_use_ssl: boolean
  imap_username: string
  imap_password: string
  smtp_host: string
  smtp_port: number
  smtp_use_ssl: boolean
  smtp_use_tls: boolean
  smtp_username: string
  smtp_password: string
  is_default?: boolean
}

export function getMailAccounts(): Promise<MailAccount[]> {
  return api.get('/api/mail/accounts/').then((r) => r.data.results ?? r.data)
}

export function createMailAccount(data: CreateMailAccountPayload): Promise<MailAccount> {
  return api.post<MailAccount>('/api/mail/accounts/', data).then((r) => r.data)
}

export function updateMailAccount(id: string, data: Partial<CreateMailAccountPayload>): Promise<MailAccount> {
  return api.patch<MailAccount>(`/api/mail/accounts/${id}/`, data).then((r) => r.data)
}

export function deleteMailAccount(id: string): Promise<void> {
  return api.delete(`/api/mail/accounts/${id}/`)
}

export function testMailConnection(id: string): Promise<{ imap: boolean; smtp: boolean; imap_error: string; smtp_error: string }> {
  return api.post(`/api/mail/accounts/${id}/test_connection/`).then((r) => r.data)
}

export function fetchMailNow(id: string): Promise<{ fetched: number }> {
  return api.post(`/api/mail/accounts/${id}/fetch_now/`).then((r) => r.data)
}

// ─── Messages ─────────────────────────────────
export interface MailAttachment {
  id: string
  filename: string
  content_type: string
  size: number
  url: string | null
}

export interface MailMessageItem {
  id: string
  account: string
  account_name: string
  account_type: string
  direction: 'in' | 'out'
  from_address: string
  from_name: string
  to_addresses: { email: string; name: string }[]
  subject: string
  status: 'unread' | 'read' | 'archived' | 'trash'
  is_starred: boolean
  has_attachments: boolean
  attachment_count: number
  sent_at: string | null
  folder: string
  protocol: string | null
}

export interface MailMessageDetail extends MailMessageItem {
  message_id: string
  in_reply_to: string
  cc_addresses: { email: string; name: string }[]
  bcc_addresses: { email: string; name: string }[]
  body_text: string
  body_html: string
  attachments: MailAttachment[]
  fetched_at: string
}

export interface MailMessagesParams {
  account?: string
  folder?: string
  direction?: 'in' | 'out'
  status?: string
  search?: string
  protocol?: string
  page?: number
}

export interface MailMessagesResponse {
  results: MailMessageItem[]
  count: number
  next: string | null
  previous: string | null
}

export function getMailMessages(params?: MailMessagesParams): Promise<MailMessagesResponse> {
  return api.get('/api/mail/messages/', { params }).then((r) => r.data)
}

export function getMailMessage(id: string): Promise<MailMessageDetail> {
  return api.get<MailMessageDetail>(`/api/mail/messages/${id}/`).then((r) => r.data)
}

export interface SendMailPayload {
  account_id: string
  to: string[]
  cc?: string[]
  bcc?: string[]
  subject: string
  body_text?: string
  body_html?: string
  reply_to_message_id?: string
  protocol_id?: string
}

export function sendMail(payload: SendMailPayload, files?: File[]): Promise<MailMessageDetail> {
  const form = new FormData()
  form.append('account_id', payload.account_id)
  payload.to.forEach((t) => form.append('to', t))
  if (payload.cc) payload.cc.forEach((c) => form.append('cc', c))
  if (payload.bcc) payload.bcc.forEach((b) => form.append('bcc', b))
  form.append('subject', payload.subject)
  if (payload.body_text) form.append('body_text', payload.body_text)
  if (payload.body_html) form.append('body_html', payload.body_html)
  if (payload.reply_to_message_id) form.append('reply_to_message_id', payload.reply_to_message_id)
  if (payload.protocol_id) form.append('protocol_id', payload.protocol_id)
  if (files) files.forEach((f) => form.append('attachments', f))
  return api
    .post<MailMessageDetail>('/api/mail/messages/send/', form, {
      transformRequest: (data, headers) => {
        if (data instanceof FormData && headers && typeof (headers as { delete?: (k: string) => void }).delete === 'function') {
          ;(headers as { delete: (k: string) => void }).delete('Content-Type')
        }
        return data
      },
    })
    .then((r) => r.data)
}

export function markRead(id: string): Promise<void> {
  return api.post(`/api/mail/messages/${id}/mark_read/`)
}

export function markUnread(id: string): Promise<void> {
  return api.post(`/api/mail/messages/${id}/mark_unread/`)
}

export function toggleStar(id: string): Promise<{ is_starred: boolean }> {
  return api.post(`/api/mail/messages/${id}/toggle_star/`).then((r) => r.data)
}

export function linkToProtocol(messageId: string, protocolId: string): Promise<void> {
  return api.post(`/api/mail/messages/${messageId}/link_protocol/`, { protocol_id: protocolId })
}

export function unlinkFromProtocol(messageId: string): Promise<void> {
  return api.post(`/api/mail/messages/${messageId}/unlink_protocol/`)
}
