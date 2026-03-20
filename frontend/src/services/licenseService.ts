import { api } from './api'

export interface LicenseInfo {
  organization_name: string
  activated_at: string | null
  expires_at: string | null
  max_users: number | null
  max_storage_gb: number | null
  features_enabled: Record<string, boolean>
}

export interface LicenseStats {
  active_users: number
  total_users: number
  storage_used_gb: number
  storage_limit_gb: number | null
  documents_count: number
  expires_in_days: number | null
  is_expired: boolean
}

export interface LicenseResponse {
  license: LicenseInfo | null
  stats: LicenseStats
}

export function getLicense(): Promise<LicenseResponse> {
  return api.get('/api/admin/license/').then((r) => r.data)
}

export interface SystemInfo {
  django_version: string
  python_version: string
  database_size_mb: number
  redis_connected: boolean
  ldap_connected: boolean
  signature_provider: string
  conservation_provider: string
}

export function getSystemInfo(): Promise<SystemInfo> {
  return api.get('/api/admin/system_info/').then((r) => r.data)
}
