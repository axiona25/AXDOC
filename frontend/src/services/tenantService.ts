import { api } from './api'

export interface TenantInfo {
  id: string
  name: string
  slug: string
  domain: string
  logo_url: string
  primary_color: string
  max_users: number
  max_storage_gb: number
  plan: string
  is_active: boolean
  created_at: string
  updated_at: string
}

export function getTenants() {
  return api.get<{ results?: TenantInfo[] } | TenantInfo[]>('/api/tenants/').then((r) => {
    const d = r.data
    return Array.isArray(d) ? d : d.results ?? []
  })
}

export function getTenantCurrent() {
  return api.get<TenantInfo>('/api/tenants/current/').then((r) => r.data)
}
