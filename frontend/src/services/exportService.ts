import { api, getAccessToken } from './api'

function buildUrl(path: string, params?: Record<string, string | undefined>): string {
  const base = (api.defaults.baseURL ?? '').replace(/\/$/, '')
  const cleanPath = path.startsWith('/') ? path : `/${path}`
  const search = new URLSearchParams()
  if (params) {
    for (const [k, v] of Object.entries(params)) {
      if (v !== undefined && v !== '') search.set(k, v)
    }
  }
  const q = search.toString()
  return `${base}${cleanPath}${q ? `?${q}` : ''}`
}

/**
 * Scarica file da endpoint export (JWT in header).
 */
export function downloadExport(path: string, params?: Record<string, string | undefined>): void {
  const url = buildUrl(path, params)
  const token = getAccessToken()
  fetch(url, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  })
    .then((res) => {
      if (!res.ok) {
        throw new Error(`Export failed: ${res.status}`)
      }
      return res.blob()
    })
    .then((blob) => {
      const a = document.createElement('a')
      a.href = URL.createObjectURL(blob)
      a.download = ''
      document.body.appendChild(a)
      a.click()
      a.remove()
      URL.revokeObjectURL(a.href)
    })
    .catch((err) => console.error('Export failed:', err))
}

export const exportProtocolsExcel = (params?: Record<string, string | undefined>) =>
  downloadExport('/api/protocols/export_excel/', params)

export const exportProtocolsPdf = (params?: Record<string, string | undefined>) =>
  downloadExport('/api/protocols/export_pdf/', params)

export const exportDossiersExcel = (params?: Record<string, string | undefined>) =>
  downloadExport('/api/dossiers/export_excel/', params)

export const exportDossiersPdf = (params?: Record<string, string | undefined>) =>
  downloadExport('/api/dossiers/export_pdf/', params)

export const exportDocumentsExcel = (params?: Record<string, string | undefined>) =>
  downloadExport('/api/documents/export_excel/', params)

export const exportAuditExcel = (params?: Record<string, string | undefined>) =>
  downloadExport('/api/audit/export_excel/', params)

export const exportAuditPdf = (params?: Record<string, string | undefined>) =>
  downloadExport('/api/audit/export_pdf/', params)

export const exportIncidentsExcel = (params?: Record<string, string | undefined>) =>
  downloadExport('/api/security-incidents/export_excel/', params)

export const exportIncidentsPdf = (params?: Record<string, string | undefined>) =>
  downloadExport('/api/security-incidents/export_pdf/', params)
