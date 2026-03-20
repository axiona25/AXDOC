import { useState, useEffect, useCallback } from 'react'
import { Link } from 'react-router-dom'
import {
  getMyFilesTree,
  getMyFiles,
  createFolder,
  downloadDocument,
  deleteDocument,
  updateDocumentVisibility,
} from '../services/documentService'
import { getMetadataStructures } from '../services/metadataService'
import type { DocumentItem, FolderItem, MyFilesTreeResponse } from '../services/documentService'
import { getAccessToken } from '../services/api'
import { UploadModal } from '../components/documents/UploadModal'
import { DocumentViewer } from '../components/viewer/DocumentViewer'
import type { MetadataStructure } from '../types/metadata'

const baseURL = import.meta.env.VITE_API_URL || ''

type TabId = 'personal' | 'office' | 'all'

function visibilityLabel(v: string): string {
  if (v === 'personal') return 'Personale'
  if (v === 'office') return 'Ufficio'
  return 'Condiviso'
}

export function MyFilesPage() {
  const [tab, setTab] = useState<TabId>('personal')
  const [tree, setTree] = useState<MyFilesTreeResponse | null>(null)
  const [documents, setDocuments] = useState<DocumentItem[]>([])
  const [selectedFolderId, setSelectedFolderId] = useState<string | null>(null)
  const [search, setSearch] = useState('')
  const [viewMode, setViewMode] = useState<'list' | 'grid'>('list')
  const [loading, setLoading] = useState(true)
  const [uploadOpen, setUploadOpen] = useState(false)
  const [uploadProgress, setUploadProgress] = useState(0)
  const [metadataStructures, setMetadataStructures] = useState<MetadataStructure[]>([])
  const [viewerDocId, setViewerDocId] = useState<string | null>(null)

  const folders: FolderItem[] = tree
    ? tab === 'office'
      ? tree.office.folders
      : tab === 'personal'
        ? tree.personal.folders
        : [...(tree.personal.folders || []), ...(tree.office.folders || [])]
    : []
  const allDocsFromTree = tree
    ? tab === 'office'
      ? tree.office.documents
      : tab === 'personal'
        ? tree.personal.documents
        : [...(tree.personal.documents || []), ...(tree.office.documents || [])]
    : []

  const loadTree = useCallback(() => {
    getMyFilesTree().then(setTree).catch(() => setTree(null))
  }, [])

  const loadDocuments = useCallback(() => {
    setLoading(true)
    const params: { section: 'my_files' | 'office'; folder_id?: string | null; title?: string } = {
      section: tab === 'office' ? 'office' : 'my_files',
    }
    if (selectedFolderId) params.folder_id = selectedFolderId
    if (search.trim()) params.title = search.trim()
    getMyFiles(params)
      .then((r) => setDocuments(r.results ?? []))
      .catch(() => setDocuments([]))
      .finally(() => setLoading(false))
  }, [tab, selectedFolderId, search])

  useEffect(() => {
    loadTree()
  }, [loadTree])

  useEffect(() => {
    loadDocuments()
  }, [loadDocuments])

  useEffect(() => {
    if (uploadOpen) {
      getMetadataStructures({ applicable_to: 'document' }).then((r) => setMetadataStructures(r.results ?? []))
    }
  }, [uploadOpen])

  const displayDocs = selectedFolderId || search.trim() ? documents : allDocsFromTree

  const handleUpload = async (data: {
    title: string
    description: string
    folderId: string | null
    file: File
    metadataStructureId?: string | null
    metadataValues?: Record<string, unknown>
    visibility?: 'personal' | 'office'
  }) => {
    const form = new FormData()
    form.append('title', data.title)
    form.append('description', data.description)
    if (data.folderId) form.append('folder_id', data.folderId)
    if (data.visibility) form.append('visibility', data.visibility)
    if (data.metadataStructureId) form.append('metadata_structure_id', data.metadataStructureId)
    if (data.metadataValues && Object.keys(data.metadataValues).length > 0) {
      form.append('metadata_values', JSON.stringify(data.metadataValues))
    }
    form.append('file', data.file)
    await new Promise<void>((resolve, reject) => {
      const xhr = new XMLHttpRequest()
      const url = `${baseURL}/api/documents/`
      const token = getAccessToken()
      xhr.open('POST', url)
      if (token) xhr.setRequestHeader('Authorization', `Bearer ${token}`)
      xhr.upload.addEventListener('progress', (e) => {
        if (e.lengthComputable) setUploadProgress(Math.round((e.loaded / e.total) * 100))
      })
      xhr.onload = () => {
        if (xhr.status >= 200 && xhr.status < 300) {
          loadTree()
          loadDocuments()
          resolve()
        } else reject(new Error(xhr.statusText))
      }
      xhr.onerror = () => reject(new Error('Network error'))
      xhr.send(form)
    })
  }

  const handleNewFolder = () => {
    const name = window.prompt('Nome cartella')
    if (!name?.trim()) return
    createFolder({ name: name.trim(), parent_id: selectedFolderId }).then(() => {
      loadTree()
      loadDocuments()
    })
  }

  const handleDownload = (doc: DocumentItem) => {
    downloadDocument(doc.id)
  }

  const handleDelete = (doc: DocumentItem) => {
    if (!window.confirm(`Eliminare "${doc.title}"?`)) return
    deleteDocument(doc.id).then(() => { loadTree(); loadDocuments() })
  }

  const handleChangeVisibility = (doc: DocumentItem, vis: 'personal' | 'office' | 'shared') => {
    updateDocumentVisibility(doc.id, vis).then(() => { loadTree(); loadDocuments() })
  }

  const handleOpenDoc = (doc: DocumentItem) => {
    setViewerDocId(doc.id)
  }

  return (
    <div className="flex h-[calc(100vh-6rem)] flex-col rounded-lg bg-white shadow">
      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-200 px-4 py-3">
        <div className="flex items-center gap-2">
          <Link to="/dashboard" className="text-sm text-indigo-600 hover:underline">← Dashboard</Link>
          <h1 className="text-xl font-semibold text-slate-800">I miei File</h1>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <input
            type="text"
            placeholder="Cerca..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="rounded border border-slate-300 px-2 py-1.5 text-sm"
          />
          <div className="flex rounded border border-slate-200 bg-slate-50">
            {(['personal', 'office', 'all'] as const).map((t) => (
              <button
                key={t}
                type="button"
                onClick={() => setTab(t)}
                className={`px-3 py-1.5 text-sm font-medium ${tab === t ? 'bg-indigo-600 text-white' : 'text-slate-600 hover:bg-slate-100'}`}
              >
                {t === 'personal' ? 'Personali' : t === 'office' ? 'Ufficio' : 'Tutti'}
              </button>
            ))}
          </div>
          <button
            type="button"
            onClick={() => setViewMode(viewMode === 'list' ? 'grid' : 'list')}
            className="rounded border border-slate-300 px-2 py-1.5 text-sm"
            title={viewMode === 'list' ? 'Griglia' : 'Lista'}
          >
            {viewMode === 'list' ? '⊞' : '≡'}
          </button>
          <button
            type="button"
            onClick={handleNewFolder}
            className="rounded bg-slate-100 px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-200"
          >
            Nuova cartella
          </button>
          <button
            type="button"
            onClick={() => setUploadOpen(true)}
            className="rounded bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700"
          >
            Carica file
          </button>
        </div>
      </div>

      <div className="flex min-h-0 flex-1">
        <div className="w-56 shrink-0 border-r border-slate-200 overflow-y-auto p-2">
          <p className="mb-2 px-2 text-xs font-medium text-slate-500">Cartelle</p>
          <button
            type="button"
            onClick={() => setSelectedFolderId(null)}
            className={`mb-1 w-full rounded px-2 py-1.5 text-left text-sm ${!selectedFolderId ? 'bg-indigo-100 text-indigo-800' : 'hover:bg-slate-100'}`}
          >
            Tutte
          </button>
          {folders.map((f) => (
            <button
              key={f.id}
              type="button"
              onClick={() => setSelectedFolderId(f.id)}
              className={`mb-1 w-full rounded px-2 py-1.5 text-left text-sm ${selectedFolderId === f.id ? 'bg-indigo-100 text-indigo-800' : 'hover:bg-slate-100'}`}
            >
              📁 {f.name}
            </button>
          ))}
        </div>

        <div className="min-w-0 flex-1 overflow-auto p-4">
          {loading ? (
            <p className="text-slate-500">Caricamento...</p>
          ) : viewMode === 'list' ? (
            <table className="w-full border-collapse text-sm">
              <thead>
                <tr className="border-b border-slate-200 bg-slate-50">
                  <th className="px-3 py-2 text-left font-medium text-slate-700">Tipo</th>
                  <th className="px-3 py-2 text-left font-medium text-slate-700">Nome</th>
                  <th className="px-3 py-2 text-left font-medium text-slate-700">Dimensione</th>
                  <th className="px-3 py-2 text-left font-medium text-slate-700">Data</th>
                  <th className="px-3 py-2 text-left font-medium text-slate-700">Visibilità</th>
                  <th className="px-3 py-2 text-left font-medium text-slate-700">Azioni</th>
                </tr>
              </thead>
              <tbody>
                {displayDocs.map((doc) => (
                  <tr
                    key={doc.id}
                    className="border-b border-slate-100 hover:bg-slate-50/50 cursor-pointer"
                    onDoubleClick={() => handleOpenDoc(doc)}
                  >
                    <td className="px-3 py-2">
                      <span title={doc.title}>
                        {doc.visibility === 'personal' ? '🔒' : doc.visibility === 'office' ? '🏢' : '🔗'}
                      </span>
                    </td>
                    <td className="px-3 py-2 font-medium text-slate-800">{doc.title}</td>
                    <td className="px-3 py-2 text-slate-600">—</td>
                    <td className="px-3 py-2 text-slate-600">
                      {doc.updated_at ? new Date(doc.updated_at).toLocaleDateString() : '—'}
                    </td>
                    <td className="px-3 py-2">
                      <span className="rounded px-1.5 py-0.5 text-xs bg-slate-100 text-slate-700">
                        {visibilityLabel(doc.visibility || 'personal')}
                      </span>
                    </td>
                    <td className="px-3 py-2">
                      <div className="flex gap-1">
                        <button type="button" onClick={() => handleOpenDoc(doc)} className="text-indigo-600 hover:underline">Apri</button>
                        <button type="button" onClick={() => handleDownload(doc)} className="text-slate-600 hover:underline">Scarica</button>
                        <button type="button" onClick={() => handleDelete(doc)} className="text-red-600 hover:underline">Elimina</button>
                        <select
                          value={doc.visibility || 'personal'}
                          onChange={(e) => handleChangeVisibility(doc, e.target.value as 'personal' | 'office' | 'shared')}
                          className="rounded border border-slate-300 text-xs"
                          onClick={(e) => e.stopPropagation()}
                        >
                          <option value="personal">Personale</option>
                          <option value="office">Ufficio</option>
                          <option value="shared">Condiviso</option>
                        </select>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : (
            <div className="grid grid-cols-2 gap-3 sm:grid-cols-4 md:grid-cols-5">
              {displayDocs.map((doc) => (
                <div
                  key={doc.id}
                  className="flex flex-col items-center rounded-lg border border-slate-200 p-3 hover:bg-slate-50 cursor-pointer"
                  onDoubleClick={() => handleOpenDoc(doc)}
                >
                  <span className="text-2xl">{doc.visibility === 'personal' ? '🔒' : doc.visibility === 'office' ? '🏢' : '📄'}</span>
                  <p className="mt-1 truncate w-full text-center text-sm font-medium text-slate-800">{doc.title}</p>
                  <p className="text-xs text-slate-500">{visibilityLabel(doc.visibility || 'personal')}</p>
                  <div className="mt-2 flex gap-1">
                    <button type="button" onClick={() => handleOpenDoc(doc)} className="text-xs text-indigo-600 hover:underline">Apri</button>
                    <button type="button" onClick={() => handleDownload(doc)} className="text-xs text-slate-600 hover:underline">Scarica</button>
                  </div>
                </div>
              ))}
            </div>
          )}
          {displayDocs.length === 0 && !loading && (
            <p className="py-8 text-center text-slate-500">Nessun file. Carica un documento o seleziona un’altra cartella.</p>
          )}
        </div>
      </div>

      <UploadModal
        open={uploadOpen}
        onClose={() => setUploadOpen(false)}
        onUpload={handleUpload}
        folders={folders}
        progress={uploadProgress}
        metadataStructures={metadataStructures}
        showVisibility
      />

      {viewerDocId && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4">
          <div className="flex h-full max-h-[90vh] w-full max-w-5xl flex-col rounded-lg bg-white shadow-xl overflow-hidden">
            <DocumentViewer
              documentId={viewerDocId}
              onClose={() => setViewerDocId(null)}
              showHeader
            />
          </div>
        </div>
      )}
    </div>
  )
}
