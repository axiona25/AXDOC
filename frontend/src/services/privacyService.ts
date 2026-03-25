import { api } from './api'

export type ConsentType =
  | 'privacy_policy'
  | 'data_processing'
  | 'marketing'
  | 'analytics'
  | 'third_party'

export interface ConsentRecord {
  id: string
  consent_type: ConsentType
  version: string
  granted: boolean
  created_at: string
}

export async function getMyConsents(): Promise<ConsentRecord[]> {
  const { data } = await api.get<ConsentRecord[]>('/api/users/my_consents/')
  return data
}

export async function grantConsent(body: {
  consent_type: ConsentType
  granted: boolean
  version: string
}): Promise<ConsentRecord> {
  const { data } = await api.post<ConsentRecord>('/api/users/my_consents/', body)
  return data
}

export async function exportMyData(): Promise<void> {
  const { data, headers } = await api.get<Blob>('/api/users/export_my_data/', {
    responseType: 'blob',
  })
  const blob = data
  const cd = headers['content-disposition'] as string | undefined
  const match = cd?.match(/filename="([^"]+)"/)
  const filename = match?.[1] ?? 'axdoc_my_data.json'
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  a.click()
  URL.revokeObjectURL(url)
}
