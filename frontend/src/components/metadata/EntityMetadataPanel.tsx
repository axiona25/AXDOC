import { useState, useEffect } from 'react'
import { getMetadataStructure, getMetadataStructures, updateFolderMetadata, updateDossierMetadata } from '../../services/metadataService'
import type { MetadataStructure, MetadataValues } from '../../types/metadata'
import { DynamicMetadataForm } from './DynamicMetadataForm'

export type EntityMetadataType = 'document' | 'dossier' | 'folder'

interface EntityMetadataPanelProps {
  entityType: EntityMetadataType
  entityId: string
  metadataStructureId: string | null
  metadataValues: MetadataValues
  canEdit: boolean
  onSave?: () => void
}

export function EntityMetadataPanel({
  entityType,
  entityId,
  metadataStructureId,
  metadataValues,
  canEdit,
  onSave,
}: EntityMetadataPanelProps) {
  const [structure, setStructure] = useState<MetadataStructure | null>(null)
  const [editMode, setEditMode] = useState(false)
  const [structures, setStructures] = useState<MetadataStructure[]>([])
  const [selectedStructureId, setSelectedStructureId] = useState<string | null>(metadataStructureId)
  const [editValues, setEditValues] = useState<MetadataValues>(metadataValues)
  const [saving, setSaving] = useState(false)
  const [errors, setErrors] = useState<Record<string, string>>({})

  const applicableTo = entityType === 'document' ? 'document' : entityType === 'dossier' ? 'dossier' : 'folder'

  useEffect(() => {
    setSelectedStructureId(metadataStructureId)
    setEditValues(metadataValues)
  }, [metadataStructureId, metadataValues])

  useEffect(() => {
    if (metadataStructureId) {
      getMetadataStructure(metadataStructureId).then(setStructure).catch(() => setStructure(null))
    } else {
      setStructure(null)
    }
  }, [metadataStructureId])

  useEffect(() => {
    if (editMode && canEdit) {
      getMetadataStructures({ applicable_to: applicableTo }).then((r) => setStructures(r.results ?? []))
    }
  }, [editMode, canEdit, applicableTo])

  const handleSave = async () => {
    setSaving(true)
    setErrors({})
    try {
      const payload = {
        metadata_structure_id: selectedStructureId || null,
        metadata_values: editValues,
      }
      if (entityType === 'folder') {
        await updateFolderMetadata(entityId, payload)
      } else if (entityType === 'dossier') {
        await updateDossierMetadata(entityId, payload)
      }
      onSave?.()
      setEditMode(false)
    } catch (err: unknown) {
      const data = (err as { response?: { data?: { metadata_values?: Record<string, string> } } })?.response?.data
      setErrors(data?.metadata_values ?? {})
    } finally {
      setSaving(false)
    }
  }

  const handleAssign = () => {
    setEditMode(true)
    setSelectedStructureId(null)
    setEditValues({})
  }

  if (!structure && !editMode) {
    return (
      <div className="rounded border border-slate-200 bg-slate-50 p-4">
        <p className="text-sm text-slate-600">Nessuna struttura metadati assegnata.</p>
        {canEdit && (
          <button
            type="button"
            onClick={handleAssign}
            className="mt-2 rounded bg-indigo-600 px-3 py-1.5 text-sm text-white hover:bg-indigo-700"
          >
            Assegna struttura
          </button>
        )}
      </div>
    )
  }

  if (editMode && canEdit) {
    return (
      <div className="space-y-3 rounded border border-slate-200 bg-white p-4">
        <label className="block text-sm font-medium text-slate-700">Struttura metadati</label>
        <select
          value={selectedStructureId ?? ''}
          onChange={(e) => {
            const id = e.target.value || null
            setSelectedStructureId(id)
            if (id) {
              getMetadataStructure(id).then((s) => {
                setStructure(s)
                setEditValues({})
              })
            } else {
              setStructure(null)
              setEditValues({})
            }
          }}
          className="w-full rounded border border-slate-300 px-3 py-2 text-sm"
        >
          <option value="">— Nessuna —</option>
          {structures.map((s) => (
            <option key={s.id} value={s.id}>{s.name}</option>
          ))}
        </select>
        {structure && (
          <DynamicMetadataForm
            structure={structure}
            values={editValues}
            onChange={setEditValues}
            errors={errors}
          />
        )}
        <div className="flex gap-2">
          <button
            type="button"
            onClick={handleSave}
            disabled={saving}
            className="rounded bg-indigo-600 px-3 py-1.5 text-sm text-white hover:bg-indigo-700 disabled:opacity-50"
          >
            {saving ? 'Salvataggio...' : 'Salva'}
          </button>
          <button
            type="button"
            onClick={() => {
              setEditMode(false)
              setSelectedStructureId(metadataStructureId)
              setEditValues(metadataValues)
            }}
            className="rounded bg-slate-200 px-3 py-1.5 text-sm text-slate-700 hover:bg-slate-300"
          >
            Annulla
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-3">
      {structure && (
        <>
          <DynamicMetadataForm
            structure={structure}
            values={metadataValues}
            onChange={() => {}}
            readOnly
          />
          {canEdit && (
            <button
              type="button"
              onClick={() => {
                setEditMode(true)
                setEditValues({ ...metadataValues })
              }}
              className="rounded bg-slate-200 px-3 py-1.5 text-sm text-slate-700 hover:bg-slate-300"
            >
              Modifica
            </button>
          )}
        </>
      )}
    </div>
  )
}
