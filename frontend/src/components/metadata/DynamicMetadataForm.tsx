import type { MetadataStructure, MetadataField, MetadataValues } from '../../types/metadata'

interface DynamicMetadataFormProps {
  structure: MetadataStructure
  values: MetadataValues
  onChange: (values: MetadataValues) => void
  errors?: Record<string, string>
  readOnly?: boolean
}

export function DynamicMetadataForm({
  structure,
  values,
  onChange,
  errors = {},
  readOnly = false,
}: DynamicMetadataFormProps) {
  const fields = (structure.fields ?? []).slice().sort((a, b) => a.order - b.order)

  const handleChange = (name: string, value: unknown) => {
    onChange({ ...values, [name]: value })
  }

  return (
    <div className="space-y-3">
      {fields.map((field) => (
        <FieldInput
          key={field.id}
          field={field}
          value={values[field.name]}
          onChange={(v) => handleChange(field.name, v)}
          error={errors[field.name]}
          readOnly={readOnly}
        />
      ))}
    </div>
  )
}

interface FieldInputProps {
  field: MetadataField
  value: unknown
  onChange: (value: unknown) => void
  error?: string
  readOnly?: boolean
}

function FieldInput({ field, value, onChange, error, readOnly }: FieldInputProps) {
  const rules = field.validation_rules || {}
  const inputId = `meta-${field.name}`
  const label = (
    <label htmlFor={inputId} className="mb-1 block text-sm font-medium text-slate-700">
      {field.label}
      {field.is_required && <span className="text-red-500"> *</span>}
    </label>
  )
  const errBlock = error && (
    <p className="mt-0.5 text-sm text-red-600" role="alert">
      {error}
    </p>
  )
  const help = field.help_text && (
    <p className="mt-0.5 text-xs text-slate-500">{field.help_text}</p>
  )

  const baseClass = "w-full rounded border border-slate-300 px-3 py-2 text-sm disabled:bg-slate-100"
  const errClass = error ? "border-red-500" : ""

  switch (field.field_type) {
    case 'text':
    case 'email':
    case 'phone':
    case 'url':
      return (
        <div>
          {label}
          <input
            id={inputId}
            type={field.field_type === 'email' ? 'email' : field.field_type === 'phone' ? 'tel' : field.field_type === 'url' ? 'url' : 'text'}
            value={String(value ?? '')}
            onChange={(e) => onChange(e.target.value || undefined)}
            className={`${baseClass} ${errClass}`}
            readOnly={readOnly}
            maxLength={(rules.max_length as number) || undefined}
          />
          {errBlock}
          {help}
        </div>
      )
    case 'textarea':
      return (
        <div>
          {label}
          <textarea
            id={inputId}
            value={String(value ?? '')}
            onChange={(e) => onChange(e.target.value || undefined)}
            className={`${baseClass} ${errClass}`}
            rows={3}
            readOnly={readOnly}
          />
          {errBlock}
          {help}
        </div>
      )
    case 'number':
      return (
        <div>
          {label}
          <input
            id={inputId}
            type="number"
            value={value !== undefined && value !== null ? String(value) : ''}
            onChange={(e) => {
              const v = e.target.value
              if (v === '') onChange(undefined)
              else onChange(Number(v))
            }}
            min={(rules.min as number) ?? undefined}
            max={(rules.max as number) ?? undefined}
            className={`${baseClass} ${errClass}`}
            readOnly={readOnly}
          />
          {errBlock}
          {help}
        </div>
      )
    case 'date':
      return (
        <div>
          {label}
          <input
            id={inputId}
            type="date"
            value={value ? String(value).slice(0, 10) : ''}
            onChange={(e) => onChange(e.target.value || undefined)}
            className={`${baseClass} ${errClass}`}
            readOnly={readOnly}
          />
          {errBlock}
          {help}
        </div>
      )
    case 'datetime':
      return (
        <div>
          {label}
          <input
            id={inputId}
            type="datetime-local"
            value={value ? String(value).slice(0, 16) : ''}
            onChange={(e) => onChange(e.target.value || undefined)}
            className={`${baseClass} ${errClass}`}
            readOnly={readOnly}
          />
          {errBlock}
          {help}
        </div>
      )
    case 'boolean':
      return (
        <div>
          <label className="flex cursor-pointer items-center gap-2">
            <input
              type="checkbox"
              id={`meta-${field.name}`}
              checked={Boolean(value)}
              onChange={(e) => onChange(e.target.checked)}
              className="h-4 w-4 rounded border-slate-300 text-indigo-600"
              readOnly={readOnly}
            />
            <span className="text-sm font-medium text-slate-700">
              {field.label}
              {field.is_required && <span className="text-red-500"> *</span>}
            </span>
          </label>
          {errBlock}
          {help}
        </div>
      )
    case 'select':
      return (
        <div>
          {label}
          <select
            id={inputId}
            value={String(value ?? '')}
            onChange={(e) => onChange(e.target.value || undefined)}
            className={`${baseClass} ${errClass}`}
            disabled={readOnly}
          >
            <option value="">— Seleziona —</option>
            {(field.options ?? []).map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>
          {errBlock}
          {help}
        </div>
      )
    case 'multiselect': {
      const arr = Array.isArray(value) ? value : value ? [value] : []
      return (
        <div>
          {label}
          <select
            id={inputId}
            multiple
            value={arr.map(String)}
            onChange={(e) => {
              const selected = Array.from(e.target.selectedOptions, (o) => o.value)
              onChange(selected.length ? selected : undefined)
            }}
            className={`${baseClass} ${errClass}`}
            disabled={readOnly}
          >
            {(field.options ?? []).map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>
          {errBlock}
          {help}
        </div>
      )
    }
    default:
      return (
        <div>
          {label}
          <input
            id={inputId}
            type="text"
            value={String(value ?? '')}
            onChange={(e) => onChange(e.target.value || undefined)}
            className={`${baseClass} ${errClass}`}
            readOnly={readOnly}
          />
          {errBlock}
          {help}
        </div>
      )
  }
}
