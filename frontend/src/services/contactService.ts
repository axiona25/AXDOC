import { api } from './api'

export interface Contact {
  id: string
  contact_type: 'person' | 'company'
  first_name: string
  last_name: string
  company_name: string
  email: string
  pec: string
  phone: string
  display_name: string
  is_favorite: boolean
  tags: string[]
}

export interface ContactDetail extends Contact {
  job_title: string
  tax_code: string
  mobile: string
  address: string
  city: string
  province: string
  zip_code: string
  country: string
  notes: string
  is_shared: boolean
  organizational_unit: string | null
  source: string
  primary_email: string
  created_by: string | null
  created_at: string
  updated_at: string
}

export interface ContactsResponse {
  results: Contact[]
  count: number
  next?: string | null
  previous?: string | null
}

export function getContacts(params?: {
  search?: string
  type?: string
  tag?: string
  favorites?: string
  page?: number
}): Promise<ContactsResponse> {
  return api.get('/api/contacts/', { params }).then((r) => r.data)
}

export function getContact(id: string): Promise<ContactDetail> {
  return api.get(`/api/contacts/${id}/`).then((r) => r.data)
}

export function createContact(data: Partial<ContactDetail>): Promise<ContactDetail> {
  return api.post('/api/contacts/', data).then((r) => r.data)
}

export function updateContact(id: string, data: Partial<ContactDetail>): Promise<ContactDetail> {
  return api.patch(`/api/contacts/${id}/`, data).then((r) => r.data)
}

export function deleteContact(id: string): Promise<void> {
  return api.delete(`/api/contacts/${id}/`)
}

export function searchContacts(q: string): Promise<Contact[]> {
  return api.get('/api/contacts/search/', { params: { q } }).then((r) => r.data)
}

export function importFromMail(): Promise<{
  total_addresses: number
  already_existing: number
  internal_skipped: number
  created: number
}> {
  return api.post('/api/contacts/import_from_mail/').then((r) => r.data)
}

export function toggleFavorite(id: string): Promise<{ is_favorite: boolean }> {
  return api.post(`/api/contacts/${id}/toggle_favorite/`).then((r) => r.data)
}
