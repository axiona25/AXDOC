import { api } from './api'

export interface DocumentTemplate {
  id: string
  name: string
  description: string
  default_status: string
  default_folder: string | null
  default_folder_name: string | null
  default_metadata_structure: string | null
  default_metadata_structure_name: string | null
  default_workflow_template: string | null
  default_workflow_template_name: string | null
  default_metadata_values: Record<string, unknown>
  auto_start_workflow: boolean
  is_active: boolean
  allowed_file_types: string[]
  max_file_size_mb: number | null
  created_by: string | null
  created_by_email: string | null
  created_at: string
  updated_at: string
}

export function getTemplates(): Promise<{ results: DocumentTemplate[]; count: number }> {
  return api.get('/api/document-templates/').then((r) => r.data)
}

export function getTemplateList(): Promise<DocumentTemplate[]> {
  return getTemplates().then((d) => d.results ?? [])
}

export function createTemplate(data: Partial<DocumentTemplate>): Promise<DocumentTemplate> {
  return api.post<DocumentTemplate>('/api/document-templates/', data).then((r) => r.data)
}

export function updateTemplate(id: string, data: Partial<DocumentTemplate>): Promise<DocumentTemplate> {
  return api.patch<DocumentTemplate>(`/api/document-templates/${id}/`, data).then((r) => r.data)
}

export function deleteTemplate(id: string): Promise<void> {
  return api.delete(`/api/document-templates/${id}/`)
}
