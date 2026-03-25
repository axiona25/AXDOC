import { api } from './api'
import { getAccessToken } from './api'

export interface ViewerInfo {
  viewer_type: string
  mime_type: string
  file_name: string
  file_size: number
}

const baseURL = import.meta.env.VITE_API_URL || ''

export interface FolderItem {
  id: string
  name: string
  parent_id: string | null
  subfolder_count: number
  document_count: number
  created_at: string
  subfolders?: FolderItem[]
}

export interface DocumentVersionItem {
  id: string
  version_number: number
  file_name: string
  file_size: number
  file_type: string
  created_by: string | null
  created_at: string
  change_description: string
  is_current: boolean
}

export interface DocumentAttachmentItem {
  id: string
  file_name: string
  file_size: number
  file_type: string
  uploaded_by: string | null
  uploaded_at: string
  description: string
  download_url?: string
}

export interface DocumentItem {
  id: string
  title: string
  description: string
  folder_id: string | null
  folder?: string | null
  folder_name?: string | null
  status: string
  current_version: number
  created_by: string | null
  created_by_email: string | null
  created_at: string
  updated_at: string
  locked_by: string | null
  locked_at: string | null
  metadata_structure?: string | { id: string; name: string; fields?: unknown[] }
  metadata_values?: Record<string, unknown>
  versions?: DocumentVersionItem[]
  attachments?: DocumentAttachmentItem[]
  can_read?: boolean
  can_write?: boolean
  can_delete?: boolean
  is_protocolled?: boolean
  visibility?: 'personal' | 'office' | 'shared'
  owner?: string | null
}

export interface DocumentsParams {
  folder_id?: string | null
  status?: string
  created_by?: string
  title?: string
  metadata_structure_id?: string
  ordering?: string
  page?: number
  /** Filtro visibilità in Documenti (GET /api/documents/) */
  visibility?: 'personal' | 'office'
  /** FASE 19: section=my_files | office per "I miei File" */
  section?: 'my_files' | 'office'
}

export interface DocumentsResponse {
  results: DocumentItem[]
  count: number
  next: string | null
  previous: string | null
}

export function getFolders(params?: { parent_id?: string | null; all?: string }): Promise<FolderItem[]> {
  return api.get<FolderItem[]>('/api/folders/', { params }).then((r) => r.data)
}

export function getFolder(id: string): Promise<FolderItem> {
  return api.get<FolderItem>(`/api/folders/${id}/`).then((r) => r.data)
}

export function getFolderBreadcrumb(id: string): Promise<FolderItem[]> {
  return api.get<FolderItem[]>(`/api/folders/${id}/breadcrumb/`).then((r) => r.data)
}

export function createFolder(data: { name: string; parent_id?: string | null }): Promise<FolderItem> {
  return api.post<FolderItem>('/api/folders/', data).then((r) => r.data)
}

export function updateFolder(id: string, data: { name: string; parent_id?: string | null }): Promise<FolderItem> {
  return api.patch<FolderItem>(`/api/folders/${id}/`, data).then((r) => r.data)
}

export function deleteFolder(id: string): Promise<void> {
  return api.delete(`/api/folders/${id}/`)
}

export function getDocuments(params?: DocumentsParams): Promise<DocumentsResponse> {
  return api.get<DocumentsResponse>('/api/documents/', { params }).then((r) => r.data)
}

/** FASE 19: documenti per sezione "I miei File" (personali o ufficio). */
export function getMyFiles(params?: { section?: 'my_files' | 'office'; folder_id?: string | null; title?: string; page?: number }): Promise<DocumentsResponse> {
  return api.get<DocumentsResponse>('/api/documents/', { params: { ...params, section: params?.section || 'my_files' } }).then((r) => r.data)
}

export interface MyFilesTreeResponse {
  personal: { folders: FolderItem[]; documents: DocumentItem[] }
  office: { folders: FolderItem[]; documents: DocumentItem[] }
}

export function getMyFilesTree(): Promise<MyFilesTreeResponse> {
  return api.get<MyFilesTreeResponse>('/api/documents/my_files_tree/').then((r) => r.data)
}

export function updateDocumentVisibility(id: string, visibility: 'personal' | 'office' | 'shared'): Promise<DocumentItem> {
  return api.patch<DocumentItem>(`/api/documents/${id}/visibility/`, { visibility }).then((r) => r.data)
}

/** FASE 19: info per viewer (tipo, mime, nome, dimensione). */
export function getViewerInfo(documentId: string): Promise<ViewerInfo> {
  return api.get<ViewerInfo>(`/api/documents/${documentId}/viewer_info/`).then((r) => r.data)
}

/** FASE 19: preview come blob URL (per iframe/img/video/audio). Ritorna object URL da revocare con URL.revokeObjectURL. */
export async function getPreviewBlobUrl(documentId: string): Promise<{ url: string; viewerType: string }> {
  const res = await api.get<Blob>(`/api/documents/${documentId}/preview/`, { responseType: 'blob' })
  const viewerType = (res.headers['x-viewer-type'] as string) || 'generic'
  const url = URL.createObjectURL(res.data)
  return { url, viewerType }
}

/** Download come blob URL (es. .p7m dove /preview/ non è disponibile). Da revocare con URL.revokeObjectURL. */
export async function getDownloadBlobUrl(documentId: string, version?: number): Promise<string> {
  const res = await api.get<Blob>(`/api/documents/${documentId}/download/`, {
    responseType: 'blob',
    params: version != null ? { version } : undefined,
  })
  return URL.createObjectURL(res.data)
}

/** FASE 19: preview come JSON (email, text). */
export function getPreviewJson<T = Record<string, unknown>>(documentId: string): Promise<T> {
  return api.get<T>(`/api/documents/${documentId}/preview/`).then((r) => r.data)
}

export function getDocument(id: string): Promise<DocumentItem> {
  return api.get<DocumentItem>(`/api/documents/${id}/`).then((r) => r.data)
}

export function uploadDocument(
  data: FormData,
  onProgress?: (percent: number) => void
): Promise<DocumentItem> {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest()
    const url = `${baseURL}/api/documents/`
    const token = getAccessToken()
    xhr.open('POST', url)
    if (token) {
      xhr.setRequestHeader('Authorization', `Bearer ${token}`)
    }
    xhr.upload.addEventListener('progress', (e) => {
      if (e.lengthComputable && onProgress) {
        onProgress(Math.round((e.loaded / e.total) * 100))
      }
    })
    xhr.onload = () => {
      if (xhr.status >= 200 && xhr.status < 300) {
        try {
          resolve(JSON.parse(xhr.responseText))
        } catch {
          reject(new Error('Invalid response'))
        }
      } else {
        try {
          const err = JSON.parse(xhr.responseText)
          reject(new Error(err.detail || err.file?.[0] || String(xhr.status)))
        } catch {
          reject(new Error(`Upload failed: ${xhr.status}`))
        }
      }
    }
    xhr.onerror = () => reject(new Error('Network error'))
    xhr.send(data)
  })
}

export function updateDocument(
  id: string,
  data: Partial<{ title: string; description: string; folder_id: string | null; metadata_values: Record<string, unknown> }>
): Promise<DocumentItem> {
  return api.patch<DocumentItem>(`/api/documents/${id}/`, data).then((r) => r.data)
}

export function deleteDocument(id: string): Promise<void> {
  return api.delete(`/api/documents/${id}/`)
}

export function uploadDocumentVersion(
  id: string,
  data: FormData,
  onProgress?: (percent: number) => void
): Promise<DocumentVersionItem> {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest()
    const url = `${baseURL}/api/documents/${id}/upload_version/`
    const token = getAccessToken()
    xhr.open('POST', url)
    if (token) {
      xhr.setRequestHeader('Authorization', `Bearer ${token}`)
    }
    xhr.upload.addEventListener('progress', (e) => {
      if (e.lengthComputable && onProgress) {
        onProgress(Math.round((e.loaded / e.total) * 100))
      }
    })
    xhr.onload = () => {
      if (xhr.status >= 200 && xhr.status < 300) {
        try {
          resolve(JSON.parse(xhr.responseText))
        } catch {
          reject(new Error('Invalid response'))
        }
      } else {
        try {
          const err = JSON.parse(xhr.responseText)
          reject(new Error(err.detail || err.file?.[0] || String(xhr.status)))
        } catch {
          reject(new Error(`Upload failed: ${xhr.status}`))
        }
      }
    }
    xhr.onerror = () => reject(new Error('Network error'))
    xhr.send(data)
  })
}

export function downloadDocument(id: string, version?: number, filename?: string): void {
  const token = getAccessToken()
  const url = version != null
    ? `${baseURL}/api/documents/${id}/download/?version=${version}`
    : `${baseURL}/api/documents/${id}/download/`
  fetch(url, { headers: token ? { Authorization: `Bearer ${token}` } : {} })
    .then((r) => r.blob())
    .then((blob) => {
      const objectUrl = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = objectUrl
      a.download = filename ?? 'document'
      a.click()
      URL.revokeObjectURL(objectUrl)
    })
}

export function getDocumentVersions(id: string): Promise<DocumentVersionItem[]> {
  return api.get<DocumentVersionItem[]>(`/api/documents/${id}/versions/`).then((r) => r.data)
}

export function lockDocument(id: string): Promise<DocumentItem> {
  return api.post<DocumentItem>(`/api/documents/${id}/lock/`).then((r) => r.data)
}

export function unlockDocument(id: string): Promise<DocumentItem> {
  return api.post<DocumentItem>(`/api/documents/${id}/unlock/`).then((r) => r.data)
}

export function copyDocument(
  id: string,
  data?: { new_title?: string; folder_id?: string | null }
): Promise<DocumentItem> {
  return api.post<DocumentItem>(`/api/documents/${id}/copy/`, data || {}).then((r) => r.data)
}

export function moveDocument(id: string, folder_id: string | null): Promise<DocumentItem> {
  return api.patch<DocumentItem>(`/api/documents/${id}/move/`, { folder_id }).then((r) => r.data)
}

export function updateDocumentMetadata(
  id: string,
  metadata_values: Record<string, unknown>
): Promise<DocumentItem> {
  return api
    .patch<DocumentItem>(`/api/documents/${id}/metadata/`, { metadata_values })
    .then((r) => r.data)
}

export function getDocumentAttachments(id: string): Promise<DocumentAttachmentItem[]> {
  return api.get<DocumentAttachmentItem[]>(`/api/documents/${id}/attachments/`).then((r) => r.data)
}

export function uploadAttachment(
  documentId: string,
  file: File,
  description?: string
): Promise<DocumentAttachmentItem> {
  const form = new FormData()
  form.append('file', file)
  if (description) form.append('description', description)
  return api
    .post<DocumentAttachmentItem>(`/api/documents/${documentId}/attachments/`, form)
    .then((r) => r.data)
}

export function deleteAttachment(documentId: string, attachmentId: string): Promise<void> {
  return api.delete(`/api/documents/${documentId}/attachments/${attachmentId}/`)
}

export function downloadAttachment(
  documentId: string,
  attachmentId: string,
  filename?: string
): void {
  const token = getAccessToken()
  const url = `${baseURL}/api/documents/${documentId}/attachments/${attachmentId}/download/`
  fetch(url, { headers: token ? { Authorization: `Bearer ${token}` } : {} })
    .then((r) => r.blob())
    .then((blob) => {
      const objectUrl = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = objectUrl
      a.download = filename ?? 'attachment'
      a.click()
      URL.revokeObjectURL(objectUrl)
    })
}
