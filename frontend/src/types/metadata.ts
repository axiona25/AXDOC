/**
 * Tipi per strutture metadati dinamiche (FASE 06).
 */
export const MetadataFieldType = {
  text: 'text',
  number: 'number',
  date: 'date',
  datetime: 'datetime',
  boolean: 'boolean',
  select: 'select',
  multiselect: 'multiselect',
  email: 'email',
  phone: 'phone',
  textarea: 'textarea',
  url: 'url',
} as const

export type MetadataFieldTypeValue = (typeof MetadataFieldType)[keyof typeof MetadataFieldType]

export interface MetadataFieldOption {
  value: string
  label: string
}

export interface MetadataField {
  id: string
  name: string
  label: string
  field_type: MetadataFieldTypeValue
  is_required: boolean
  is_searchable: boolean
  order: number
  options: MetadataFieldOption[]
  default_value: unknown
  validation_rules: Record<string, unknown>
  help_text: string
}

export interface MetadataStructure {
  id: string
  name: string
  description: string
  allowed_file_extensions: string[]
  allowed_organizational_units?: string[]
  is_active: boolean
  created_at: string
  updated_at: string
  fields?: MetadataField[]
  field_count?: number
  document_count?: number
}

export type MetadataValues = Record<string, unknown>
