import { api } from './api'

export type SearchScope =
  | 'all'
  | 'documents'
  | 'protocols'
  | 'dossiers'
  | 'contacts'

export interface SearchParams {
  q?: string
  type?: SearchScope
  folder_id?: string
  metadata_structure_id?: string
  status?: string
  created_by?: string
  date_from?: string
  date_to?: string
  order_by?: string
  page?: number
  page_size?: number
  [key: `metadata_${string}`]: string | undefined
}

export interface SearchResultItem {
  id: string
  type?: 'document' | 'protocol' | 'dossier' | 'contact'
  title: string
  description?: string
  status?: string
  current_version?: number
  created_at?: string
  updated_at?: string
  created_by_id?: string | null
  folder_id?: string | null
  folder_name?: string | null
  metadata_structure_id?: string | null
  snippet?: string | null
  score?: number | null
  subtitle?: string
  url?: string
}

export interface SearchResponse {
  results: SearchResultItem[]
  total_count: number
  facets: Record<string, number | Record<string, number> | undefined>
  type?: string
}

export function search(params: SearchParams): Promise<SearchResponse> {
  const clean: Record<string, string | number> = {}
  Object.entries(params).forEach(([k, v]) => {
    if (v !== undefined && v !== '' && v !== null) clean[k] = v as string | number
  })
  return api.get<SearchResponse>('/api/search/', { params: clean }).then((r) => r.data)
}
