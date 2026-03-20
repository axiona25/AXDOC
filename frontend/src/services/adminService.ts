import { api } from './api'

export interface SystemSettingsData {
  email: Record<string, unknown>
  organization: Record<string, unknown>
  protocol: Record<string, unknown>
  security: Record<string, unknown>
  storage: Record<string, unknown>
  ldap: Record<string, unknown>
  conservation: Record<string, unknown>
  updated_at: string | null
}

export function getSettings(): Promise<SystemSettingsData> {
  return api.get<SystemSettingsData>('/api/admin/settings/').then((r) => r.data)
}

export function patchSettings(data: Partial<SystemSettingsData>): Promise<SystemSettingsData> {
  return api.patch<SystemSettingsData>('/api/admin/settings/', data).then((r) => r.data)
}

export function testEmail(to?: string): Promise<{ status: string; detail: string }> {
  return api.post<{ status: string; detail: string }>('/api/admin/settings/test_email/', to != null ? { to } : {}).then((r) => r.data)
}

export function testLdap(): Promise<{ status: string; detail: string }> {
  return api.post<{ status: string; detail: string }>('/api/admin/settings/test_ldap/').then((r) => r.data)
}
