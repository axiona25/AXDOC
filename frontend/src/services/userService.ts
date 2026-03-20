import { api } from './api'
import type { User } from '../types/auth'

export interface UsersParams {
  role?: string
  user_type?: 'internal' | 'guest'
  is_active?: boolean
  search?: string
  page?: number
}

export interface UsersResponse {
  results: User[]
  count: number
  next: string | null
  previous: string | null
}

export function getUsers(params?: UsersParams): Promise<UsersResponse> {
  return api.get('/api/users/', { params }).then((r) => r.data)
}

export function getUser(id: string): Promise<User> {
  return api.get(`/api/users/${id}/`).then((r) => r.data)
}

export interface CreateUserData {
  email: string
  first_name: string
  last_name: string
  role: string
  phone?: string
}

export function createUser(data: CreateUserData): Promise<User> {
  return api.post('/api/users/', data).then((r) => r.data)
}

export interface CreateUserManualData {
  email: string
  first_name: string
  last_name: string
  user_type: 'internal' | 'guest'
  role?: string
  organizational_unit_id?: string | null
  password?: string
  send_welcome_email?: boolean
}

export function createUserManual(data: CreateUserManualData): Promise<User> {
  return api.post<User>('/api/users/create_manual/', data).then((r) => r.data)
}

export function changeUserType(userId: string, userType: 'internal' | 'guest'): Promise<User> {
  return api.post<User>(`/api/users/${userId}/change_type/`, { user_type: userType }).then((r) => r.data)
}

export interface UpdateUserData {
  first_name?: string
  last_name?: string
  role?: string
  user_type?: 'internal' | 'guest'
  is_active?: boolean
  organizational_unit_id?: string | null
}

export function updateUser(id: string, data: UpdateUserData): Promise<User> {
  return api.patch(`/api/users/${id}/`, data).then((r) => r.data)
}

export function deleteUser(id: string): Promise<void> {
  return api.delete(`/api/users/${id}/`)
}

export interface InviteUserData {
  email: string
  role: string
  organizational_unit_id?: string
  ou_role?: string
}

export function inviteUser(data: InviteUserData): Promise<{ id: string; email: string }> {
  return api.post('/api/auth/invite/', data).then((r) => r.data)
}

export function downloadImportTemplate(format: 'csv' | 'xlsx'): Promise<void> {
  const contentType = format === 'csv' ? 'text/csv' : 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
  const filename = format === 'csv' ? 'template_utenti.csv' : 'template_utenti.xlsx'
  return api
    .get(`/api/users/import/template/?format=${format}`, { responseType: 'blob' })
    .then((r) => {
      const url = window.URL.createObjectURL(new Blob([r.data], { type: contentType }))
      const a = document.createElement('a')
      a.href = url
      a.download = filename
      a.click()
      window.URL.revokeObjectURL(url)
    })
}

export interface ImportPreviewRow {
  row: number
  email: string
  name: string
  valid: boolean
  errors: string[]
}

export interface ImportPreviewResponse {
  total_rows: number
  valid_rows: number
  invalid_rows: number
  preview: ImportPreviewRow[]
}

export function importPreview(file: File): Promise<ImportPreviewResponse> {
  const form = new FormData()
  form.append('file', file)
  return api.post<ImportPreviewResponse>('/api/users/import/preview/', form, {
    headers: { 'Content-Type': 'multipart/form-data' },
  }).then((r) => r.data)
}

export interface ImportResult {
  total: number
  created: number
  skipped: number
  errors: { row: number; email: string; errors: string[] }[]
}

export function importUsers(file: File, sendInvite: boolean): Promise<ImportResult> {
  const form = new FormData()
  form.append('file', file)
  form.append('send_invite', sendInvite ? 'true' : 'false')
  return api.post<ImportResult>('/api/users/import/', form, {
    headers: { 'Content-Type': 'multipart/form-data' },
  }).then((r) => r.data)
}
