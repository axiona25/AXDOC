import { useState } from 'react'
import type { MetadataStructure } from '../../types/metadata'
import type { CreateMetadataStructureData } from '../../services/metadataService'

const FIELD_TYPES = [
  { value: 'text', label: 'Testo' },
  { value: 'number', label: 'Numero' },
  { value: 'date', label: 'Data' },
  { value: 'datetime', label: 'Data e ora' },
  { value: 'boolean', label: 'Sì/No' },
  { value: 'select', label: 'Selezione singola' },
  { value: 'multiselect', label: 'Selezione multipla' },
  { value: 'email', label: 'Email' },
  { value: 'phone', label: 'Telefono' },
  { value: 'textarea', label: 'Testo lungo' },
  { value: 'url', label: 'URL' },
]

interface MetadataStructureFormProps {
  structure: MetadataStructure | null
  onSubmit: (data: CreateMetadataStructureData) => Promise<void>
  onCancel: () => void
}

interface FieldForm {
  id?: string
  name: string
  label: string
  field_type: string
  is_required: boolean
  is_searchable: boolean
  order: number
  options: Array<{ value: string; label: string }>
  validation_rules: { min?: number; max?: number }
  help_text: string
}

export function MetadataStructureForm({
  structure,
  onSubmit,
  onCancel,
}: MetadataStructureFormProps) {
  const [name, setName] = useState(structure?.name ?? '')
  const [description, setDescription] = useState(structure?.description ?? '')
  const [allowedExtensions, setAllowedExtensions] = useState(
    structure?.allowed_file_extensions?.join(', ') ?? ''
  )
  const [fields, setFields] = useState<FieldForm[]>(() =>
    (structure?.fields ?? []).map((f) => ({
      id: f.id,
      name: f.name,
      label: f.label,
      field_type: f.field_type,
      is_required: f.is_required,
      is_searchable: f.is_searchable,
      order: f.order,
      options: f.options ?? [],
      validation_rules: (f.validation_rules as { min?: number; max?: number }) ?? {},
      help_text: f.help_text ?? '',
    }))
  )
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')

  const addField = () => {
    setFields((prev) => [
      ...prev,
      {
        name: `campo_${prev.length + 1}`,
        label: `Campo ${prev.length + 1}`,
        field_type: 'text',
        is_required: false,
        is_searchable: true,
        order: prev.length,
        options: [],
        validation_rules: {},
        help_text: '',
      },
    ])
  }

  const updateField = (index: number, patch: Partial<FieldForm>) => {
    setFields((prev) => {
      const next = [...prev]
      next[index] = { ...next[index], ...patch }
      if (patch.label !== undefined && !patch.name) {
        next[index].name = patch.label
          .toLowerCase()
          .replace(/\s+/g, '_')
          .replace(/[^a-z0-9_]/g, '')
      }
      return next
    })
  }

  const removeField = (index: number) => {
    setFields((prev) => prev.filter((_, i) => i !== index))
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    if (!name.trim()) {
      setError('Nome obbligatorio.')
      return
    }
    setSaving(true)
    try {
      await onSubmit({
        name: name.trim(),
        description: description.trim(),
        allowed_file_extensions: allowedExtensions
          .split(',')
          .map((x) => x.trim())
          .filter(Boolean)
          .map((x) => (x.startsWith('.') ? x : `.${x}`)),
        fields: fields.map((f, i) => ({
          id: f.id,
          name: f.name || `field_${i}`,
          label: f.label || f.name,
          field_type: f.field_type,
          is_required: f.is_required,
          is_searchable: f.is_searchable,
          order: i,
          options: f.options,
          validation_rules: f.validation_rules,
          help_text: f.help_text,
        })),
      })
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Salvataggio fallito.')
    } finally {
      setSaving(false)
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div>
        <label htmlFor="meta-structure-name" className="mb-1 block text-sm font-medium text-slate-700">Nome *</label>
        <input
          id="meta-structure-name"
          type="text"
          value={name}
          onChange={(e) => setName(e.target.value)}
          className="w-full rounded border border-slate-300 px-3 py-2 text-sm"
          maxLength={200}
        />
      </div>
      <div>
        <label htmlFor="meta-structure-desc" className="mb-1 block text-sm font-medium text-slate-700">Descrizione</label>
        <textarea
          id="meta-structure-desc"
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          className="w-full rounded border border-slate-300 px-3 py-2 text-sm"
          rows={2}
        />
      </div>
      <div>
        <label className="mb-1 block text-sm font-medium text-slate-700">
          Estensioni file consentite (virgola, es. .pdf, .docx)
        </label>
        <input
          type="text"
          value={allowedExtensions}
          onChange={(e) => setAllowedExtensions(e.target.value)}
          className="w-full rounded border border-slate-300 px-3 py-2 text-sm"
          placeholder=".pdf, .docx"
        />
      </div>
      <div>
        <div className="mb-2 flex items-center justify-between">
          <span className="text-sm font-medium text-slate-700">Campi</span>
          <button type="button" onClick={addField} className="rounded bg-indigo-600 px-2 py-1 text-sm text-white hover:bg-indigo-700">
            + Aggiungi campo
          </button>
        </div>
        <div className="space-y-3 rounded border border-slate-200 p-3">
          {fields.map((f, i) => (
            <div key={i} className="rounded border border-slate-100 bg-slate-50 p-3">
              <div className="mb-2 flex justify-between">
                <span className="text-sm font-medium">Campo {i + 1}</span>
                <button type="button" onClick={() => removeField(i)} className="text-red-600 hover:underline">
                  Rimuovi
                </button>
              </div>
              <div className="grid grid-cols-2 gap-2">
                <input
                  type="text"
                  placeholder="Nome tecnico"
                  value={f.name}
                  onChange={(e) => updateField(i, { name: e.target.value })}
                  className="rounded border border-slate-300 px-2 py-1 text-sm"
                />
                <input
                  type="text"
                  placeholder="Etichetta"
                  value={f.label}
                  onChange={(e) => updateField(i, { label: e.target.value })}
                  className="rounded border border-slate-300 px-2 py-1 text-sm"
                />
                <select
                  value={f.field_type}
                  onChange={(e) => updateField(i, { field_type: e.target.value })}
                  className="rounded border border-slate-300 px-2 py-1 text-sm"
                >
                  {FIELD_TYPES.map((t) => (
                    <option key={t.value} value={t.value}>{t.label}</option>
                  ))}
                </select>
                <label className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    checked={f.is_required}
                    onChange={(e) => updateField(i, { is_required: e.target.checked })}
                  />
                  <span className="text-sm">Obbligatorio</span>
                </label>
                {(f.field_type === 'select' || f.field_type === 'multiselect') && (
                  <div className="col-span-2">
                    <span className="text-xs text-slate-600">Opzioni (value, label per riga)</span>
                    <textarea
                      value={f.options.map((o) => `${o.value},${o.label}`).join('\n')}
                      onChange={(e) => {
                        const opts = e.target.value
                          .split('\n')
                          .map((line) => {
                            const [v, l] = line.split(',').map((x) => x.trim())
                            return v ? { value: v, label: l || v } : null
                          })
                          .filter(Boolean) as Array<{ value: string; label: string }>
                        updateField(i, { options: opts })
                      }}
                      className="mt-1 w-full rounded border border-slate-300 px-2 py-1 text-sm"
                      rows={3}
                    />
                  </div>
                )}
                {f.field_type === 'number' && (
                  <>
                    <input
                      type="number"
                      placeholder="Min"
                      value={f.validation_rules.min ?? ''}
                      onChange={(e) =>
                        updateField(i, {
                          validation_rules: {
                            ...f.validation_rules,
                            min: e.target.value === '' ? undefined : Number(e.target.value),
                          },
                        })
                      }
                      className="rounded border border-slate-300 px-2 py-1 text-sm"
                    />
                    <input
                      type="number"
                      placeholder="Max"
                      value={f.validation_rules.max ?? ''}
                      onChange={(e) =>
                        updateField(i, {
                          validation_rules: {
                            ...f.validation_rules,
                            max: e.target.value === '' ? undefined : Number(e.target.value),
                          },
                        })
                      }
                      className="rounded border border-slate-300 px-2 py-1 text-sm"
                    />
                  </>
                )}
              </div>
            </div>
          ))}
        </div>
      </div>
      {error && <p className="text-sm text-red-600">{error}</p>}
      <div className="flex justify-end gap-2">
        <button type="button" onClick={onCancel} className="rounded bg-slate-200 px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-300">
          Annulla
        </button>
        <button type="submit" disabled={saving} className="rounded bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-50">
          {saving ? 'Salvataggio...' : 'Salva'}
        </button>
      </div>
    </form>
  )
}
