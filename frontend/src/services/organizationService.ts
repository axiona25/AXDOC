import { api } from './api'

export interface OrganizationalUnit {
  id: string
  name: string
  code: string
  description: string
  parent: string | null
  is_active: boolean
  created_at: string
  updated_at: string
  children?: OrganizationalUnit[]
  members_count?: number
  members?: OUMember[]
}

export interface OUMember {
  id: string
  user: string
  user_email: string
  user_name: string
  role: string
  joined_at: string
  is_active: boolean
}

export interface OrganizationsParams {
  mine?: boolean
  is_active?: boolean
  parent?: string | null
  code?: string
  name?: string
  page?: number
}

export interface OrganizationsResponse {
  results: OrganizationalUnit[]
  count: number
  next: string | null
  previous: string | null
}

export function getOrganizationalUnits(params?: OrganizationsParams): Promise<OrganizationsResponse> {
  return api.get('/api/organizations/', { params }).then((r) => r.data)
}

export function getOrganizationalUnitTree(): Promise<OrganizationalUnit[]> {
  return api.get('/api/organizations/tree/').then((r) => r.data)
}

export function getOrganizationalUnit(id: string): Promise<OrganizationalUnit> {
  return api.get(`/api/organizations/${id}/`).then((r) => r.data)
}

export function getOUMembers(ouId: string, params?: { role?: string }): Promise<OUMember[]> {
  return api.get(`/api/organizations/${ouId}/members/`, { params }).then((r) => r.data)
}

export function createOrganizationalUnit(data: {
  name: string
  code: string
  description?: string
  parent?: string | null
}): Promise<OrganizationalUnit> {
  return api.post('/api/organizations/', data).then((r) => r.data)
}

export function updateOrganizationalUnit(
  id: string,
  data: { name?: string; code?: string; description?: string; parent?: string | null }
): Promise<OrganizationalUnit> {
  return api.patch(`/api/organizations/${id}/`, data).then((r) => r.data)
}

export function addMember(ouId: string, userId: string, role: string): Promise<OUMember> {
  return api.post(`/api/organizations/${ouId}/add_member/`, { user_id: userId, role }).then((r) => r.data)
}

export function removeMember(ouId: string, userId: string): Promise<void> {
  return api.delete(`/api/organizations/${ouId}/remove_member/${userId}/`)
}

export function exportMembers(ouId: string): Promise<Blob> {
  return api
    .get(`/api/organizations/${ouId}/export/`, { responseType: 'blob' })
    .then((r) => r.data)
}
