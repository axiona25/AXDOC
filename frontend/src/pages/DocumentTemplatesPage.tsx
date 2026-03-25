import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { useAuthStore } from '../store/authStore'
import { getTemplates, deleteTemplate, updateTemplate } from '../services/templateService'
import type { DocumentTemplate } from '../services/templateService'
import { TemplateFormModal } from '../components/documents/TemplateFormModal'

export function DocumentTemplatesPage() {
  const user = useAuthStore((s) => s.user)
  const [items, setItems] = useState<DocumentTemplate[]>([])
  const [loading, setLoading] = useState(true)
  const [formOpen, setFormOpen] = useState(false)
  const [editing, setEditing] = useState<DocumentTemplate | null>(null)

  const load = () => {
    setLoading(true)
    getTemplates()
      .then((r) => setItems(r.results ?? []))
      .catch(() => setItems([]))
      .finally(() => setLoading(false))
  }

  useEffect(() => {
    load()
  }, [])

  if (user?.role !== 'ADMIN') {
    return (
      <div className="p-6">
        <p className="text-slate-600">Accesso riservato agli amministratori.</p>
        <Link to="/dashboard" className="text-indigo-600 hover:underline">
          Dashboard
        </Link>
      </div>
    )
  }

  const handleDelete = async (t: DocumentTemplate) => {
    if (!confirm(`Eliminare il template "${t.name}"?`)) return
    await deleteTemplate(t.id)
    load()
  }

  const toggleActive = async (t: DocumentTemplate) => {
    await updateTemplate(t.id, { is_active: !t.is_active })
    load()
  }

  return (
    <div className="min-h-screen bg-slate-100 p-4 md:p-6">
      <div className="mx-auto max-w-6xl">
        <div className="mb-4 flex flex-wrap items-center justify-between gap-2">
          <h1 className="text-xl font-bold text-slate-800">Template documenti</h1>
          <div className="flex gap-2">
            <Link to="/dashboard" className="rounded border border-slate-300 bg-white px-3 py-1.5 text-sm hover:bg-slate-50">
              Dashboard
            </Link>
            <button
              type="button"
              onClick={() => {
                setEditing(null)
                setFormOpen(true)
              }}
              className="rounded bg-indigo-600 px-4 py-1.5 text-sm font-medium text-white hover:bg-indigo-700"
            >
              Nuovo template
            </button>
          </div>
        </div>
        <div className="overflow-hidden rounded-lg border border-slate-200 bg-white shadow">
          {loading ? (
            <p className="p-6 text-slate-500">Caricamento...</p>
          ) : (
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-slate-200 bg-slate-50 text-left">
                  <th className="p-3 font-medium">Nome</th>
                  <th className="p-3 font-medium">Descrizione</th>
                  <th className="p-3 font-medium">Cartella</th>
                  <th className="p-3 font-medium">Metadati</th>
                  <th className="p-3 font-medium">Workflow</th>
                  <th className="p-3 font-medium">Stato</th>
                  <th className="p-3 font-medium text-right">Azioni</th>
                </tr>
              </thead>
              <tbody>
                {items.map((t) => (
                  <tr key={t.id} className="border-b border-slate-100">
                    <td className="p-3 font-medium text-slate-800">{t.name}</td>
                    <td className="max-w-[200px] truncate p-3 text-slate-600" title={t.description}>
                      {t.description || '—'}
                    </td>
                    <td className="p-3 text-slate-600">{t.default_folder_name ?? '—'}</td>
                    <td className="p-3 text-slate-600">{t.default_metadata_structure_name ?? '—'}</td>
                    <td className="p-3 text-slate-600">{t.default_workflow_template_name ?? '—'}</td>
                    <td className="p-3">
                      <span
                        className={`rounded-full px-2 py-0.5 text-xs font-medium ${
                          t.is_active ? 'bg-emerald-100 text-emerald-800' : 'bg-slate-200 text-slate-600'
                        }`}
                      >
                        {t.is_active ? 'Attivo' : 'Disattivo'}
                      </span>
                    </td>
                    <td className="p-3 text-right">
                      <button
                        type="button"
                        onClick={() => {
                          setEditing(t)
                          setFormOpen(true)
                        }}
                        className="mr-2 text-indigo-600 hover:underline"
                      >
                        Modifica
                      </button>
                      <button type="button" onClick={() => toggleActive(t)} className="mr-2 text-slate-600 hover:underline">
                        {t.is_active ? 'Disattiva' : 'Attiva'}
                      </button>
                      <button type="button" onClick={() => handleDelete(t)} className="text-red-600 hover:underline">
                        Elimina
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>
      <TemplateFormModal
        open={formOpen}
        onClose={() => {
          setFormOpen(false)
          setEditing(null)
        }}
        onSaved={load}
        initial={editing}
      />
    </div>
  )
}
