import { api } from './api'

export type IncidentSeverity = 'low' | 'medium' | 'high' | 'critical'
export type IncidentStatus = 'open' | 'investigating' | 'mitigated' | 'resolved' | 'closed'
export type IncidentCategory =
  | 'unauthorized_access'
  | 'data_breach'
  | 'malware'
  | 'phishing'
  | 'dos'
  | 'misconfiguration'
  | 'other'

export interface SecurityIncident {
  id: string
  title: string
  description: string
  severity: IncidentSeverity
  status: IncidentStatus
  category: IncidentCategory
  affected_systems: string
  affected_users_count: number
  data_compromised: boolean
  containment_actions: string
  remediation_actions: string
  reported_to_authority: boolean
  authority_report_date: string | null
  authority_reference: string
  reported_by: string | null
  reported_by_email: string | null
  assigned_to: string | null
  assigned_to_email: string | null
  detected_at: string
  created_at: string
  updated_at: string
  resolved_at: string | null
}

export type SecurityIncidentPayload = Partial<
  Omit<
    SecurityIncident,
    | 'id'
    | 'reported_by'
    | 'reported_by_email'
    | 'assigned_to_email'
    | 'created_at'
    | 'updated_at'
  >
> &
  Pick<SecurityIncident, 'title' | 'description' | 'severity' | 'category' | 'detected_at'>

export async function fetchSecurityIncidents(
  params?: Record<string, string | undefined>,
): Promise<{ results: SecurityIncident[]; count: number }> {
  const { data } = await api.get<{ results: SecurityIncident[]; count: number }>(
    '/api/security-incidents/',
    { params },
  )
  return data
}

export async function getSecurityIncident(id: string): Promise<SecurityIncident> {
  const { data } = await api.get<SecurityIncident>(`/api/security-incidents/${id}/`)
  return data
}

export async function createSecurityIncident(
  body: SecurityIncidentPayload,
): Promise<SecurityIncident> {
  const { data } = await api.post<SecurityIncident>('/api/security-incidents/', body)
  return data
}

export async function updateSecurityIncident(
  id: string,
  body: Partial<SecurityIncidentPayload>,
): Promise<SecurityIncident> {
  const { data } = await api.patch<SecurityIncident>(`/api/security-incidents/${id}/`, body)
  return data
}

export async function deleteSecurityIncident(id: string): Promise<void> {
  await api.delete(`/api/security-incidents/${id}/`)
}
