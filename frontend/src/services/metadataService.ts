import { api } from './api'
import type { MetadataStructure, MetadataValues } from '../types/metadata'

export interface MetadataStructuresParams {
  is_active?: boolean
  usable_by_me?: boolean
  applicable_to?: 'document' | 'folder' | 'dossier' | 'email'
  page?: number
}

export interface MetadataStructuresResponse {
  results: MetadataStructure[]
  count: number
  next: string | null
  previous: string | null
}

export function getMetadataStructures(
  params?: MetadataStructuresParams
): Promise<MetadataStructuresResponse> {
  return api.get<MetadataStructuresResponse>('/api/metadata/structures/', { params }).then((r) => r.data)
}

export function getMetadataStructure(id: string): Promise<MetadataStructure> {
  return api.get<MetadataStructure>(`/api/metadata/structures/${id}/`).then((r) => r.data)
}

export interface CreateMetadataStructureData {
  name: string
  description?: string
  allowed_file_extensions?: string[]
  allowed_organizational_units?: string[]
  is_active?: boolean
  fields?: Array<{
    name: string
    label: string
    field_type: string
    is_required?: boolean
    is_searchable?: boolean
    order?: number
    options?: Array<{ value: string; label: string }>
    default_value?: unknown
    validation_rules?: Record<string, unknown>
    help_text?: string
  }>
}

export function createMetadataStructure(data: CreateMetadataStructureData): Promise<MetadataStructure> {
  return api.post<MetadataStructure>('/api/metadata/structures/', data).then((r) => r.data)
}

export function updateMetadataStructure(
  id: string,
  data: Partial<CreateMetadataStructureData>
): Promise<MetadataStructure> {
  return api.patch<MetadataStructure>(`/api/metadata/structures/${id}/`, data).then((r) => r.data)
}

export function deleteMetadataStructure(id: string): Promise<void> {
  return api.delete(`/api/metadata/structures/${id}/`)
}

export function getStructureDocuments(structureId: string): Promise<unknown[]> {
  return api.get<unknown[]>(`/api/metadata/structures/${structureId}/documents/`).then((r) => r.data)
}

export interface ValidateMetadataResponse {
  valid: boolean
  errors: Array<{ field: string; message: string }>
}

export function validateMetadata(
  structureId: string,
  values: MetadataValues
): Promise<ValidateMetadataResponse> {
  return api
    .post<ValidateMetadataResponse>(`/api/metadata/structures/${structureId}/validate/`, { values })
    .then((r) => r.data)
}

export interface FolderMetadataPayload {
  metadata_structure_id?: string | null
  metadata_values?: MetadataValues
}

export function updateFolderMetadata(
  folderId: string,
  data: FolderMetadataPayload
): Promise<{ id: string; metadata_structure: string | null; metadata_values: MetadataValues }> {
  return api.patch(`/api/folders/${folderId}/metadata/`, data).then((r) => r.data)
}

export interface DossierMetadataPayload {
  metadata_structure_id?: string | null
  metadata_values?: MetadataValues
}

export function updateDossierMetadata(
  dossierId: string,
  data: DossierMetadataPayload
): Promise<{ id: string; metadata_structure: string | null; metadata_values: MetadataValues }> {
  return api.patch(`/api/dossiers/${dossierId}/metadata/`, data).then((r) => r.data)
}
