import { useState, useEffect } from 'react'
import {
  getMetadataStructures,
  getMetadataStructure,
  createMetadataStructure,
  updateMetadataStructure,
  deleteMetadataStructure,
} from '../services/metadataService'
import type { MetadataStructure } from '../types/metadata'
import type { CreateMetadataStructureData } from '../services/metadataService'
import { MetadataStructureTable } from '../components/metadata/MetadataStructureTable'
import { MetadataStructureForm } from '../components/metadata/MetadataStructureForm'
import { MetadataPreviewModal } from '../components/metadata/MetadataPreviewModal'

export function MetadataPage() {
  const [structures, setStructures] = useState<MetadataStructure[]>([])
  const [loading, setLoading] = useState(true)
  const [filterActive, setFilterActive] = useState<boolean | null>(null)
  const [editing, setEditing] = useState<MetadataStructure | null>(null)
  const [preview, setPreview] = useState<MetadataStructure | null>(null)
  const [createNew, setCreateNew] = useState(false)

  const load = () => {
    setLoading(true)
    getMetadataStructures({
      is_active: filterActive === null ? undefined : filterActive,
    })
      .then((r) => setStructures(r.results ?? []))
      .finally(() => setLoading(false))
  }

  useEffect(() => {
    load()
  }, [filterActive])

  const handleEdit = (s: MetadataStructure) => {
    getMetadataStructure(s.id).then((full) => {
      setEditing(full)
      setCreateNew(false)
    })
  }

  const handlePreview = (s: MetadataStructure) => {
    getMetadataStructure(s.id).then(setPreview)
  }

  const handleDelete = async (s: MetadataStructure) => {
    if (!window.confirm(`Eliminare la struttura "${s.name}"?`)) return
    try {
      await deleteMetadataStructure(s.id)
      load()
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Eliminazione fallita.')
    }
  }

  const handleSubmit = async (data: CreateMetadataStructureData) => {
    if (editing) {
      await updateMetadataStructure(editing.id, data)
    } else {
      await createMetadataStructure(data)
    }
    setEditing(null)
    setCreateNew(false)
    load()
  }

  return (
    <div className="min-h-screen bg-slate-50 p-6">
      <div className="mx-auto max-w-5xl">
        <div className="mb-6 flex items-center justify-between">
          <h1 className="text-2xl font-bold text-slate-800">Strutture metadati</h1>
          <div className="flex gap-2">
            <select
              value={filterActive === null ? 'all' : String(filterActive)}
              onChange={(e) =>
                setFilterActive(
                  e.target.value === 'all' ? null : e.target.value === 'true'
                )
              }
              className="rounded border border-slate-300 px-3 py-1.5 text-sm"
            >
              <option value="all">Tutte</option>
              <option value="true">Attive</option>
              <option value="false">Inattive</option>
            </select>
            <button
              type="button"
              onClick={() => {
                setEditing(null)
                setCreateNew(true)
              }}
              className="rounded bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700"
            >
              Nuova struttura
            </button>
          </div>
        </div>
        {loading ? (
          <p className="text-slate-500">Caricamento...</p>
        ) : (
          <MetadataStructureTable
            structures={structures}
            onEdit={handleEdit}
            onPreview={handlePreview}
            onDelete={handleDelete}
          />
        )}
      </div>

      {(editing || createNew) && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
          <div className="max-h-[90vh] w-full max-w-2xl overflow-auto rounded-lg bg-white p-6 shadow-xl">
            <h2 className="mb-4 text-lg font-semibold text-slate-800">
              {editing ? `Modifica: ${editing.name}` : 'Nuova struttura metadati'}
            </h2>
            <MetadataStructureForm
              structure={editing}
              onSubmit={handleSubmit}
              onCancel={() => {
                setEditing(null)
                setCreateNew(false)
              }}
            />
          </div>
        </div>
      )}

      <MetadataPreviewModal
        open={!!preview}
        onClose={() => setPreview(null)}
        structure={preview}
      />
    </div>
  )
}
