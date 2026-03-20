import { api } from './api'

export interface UserGroup {
  id: string
  name: string
  description: string
  created_at: string
  updated_at: string
  is_active: boolean
  members_count: number
}

export interface UserGroupMember {
  id: string
  user: string
  user_email: string
  user_name: string
  added_at: string
}

export interface GroupsResponse {
  results: UserGroup[]
  count: number
  next: string | null
  previous: string | null
}

export function getGroups(params?: { search?: string }): Promise<GroupsResponse> {
  return api.get('/api/groups/', { params }).then((r) => r.data)
}

export function getGroup(id: string): Promise<UserGroup & { members: UserGroupMember[] }> {
  return api.get(`/api/groups/${id}/`).then((r) => r.data)
}

export function createGroup(data: { name: string; description?: string }): Promise<UserGroup> {
  return api.post('/api/groups/', data).then((r) => r.data)
}

export function updateGroup(id: string, data: { name?: string; description?: string }): Promise<UserGroup> {
  return api.patch(`/api/groups/${id}/`, data).then((r) => r.data)
}

export function deleteGroup(id: string): Promise<void> {
  return api.delete(`/api/groups/${id}/`)
}

export function addGroupMembers(groupId: string, userIds: string[]): Promise<{ added: number }> {
  return api.post(`/api/groups/${groupId}/add_members/`, { user_ids: userIds }).then((r) => r.data)
}

export function removeGroupMember(groupId: string, userId: string): Promise<void> {
  return api.delete(`/api/groups/${groupId}/remove_member/${userId}/`)
}

export function getGroupMembers(groupId: string): Promise<UserGroupMember[]> {
  return api.get(`/api/groups/${groupId}/members/`).then((r) => r.data)
}
