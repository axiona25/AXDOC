import { useState, useCallback, useEffect, useRef } from 'react'
import { Sparkles } from 'lucide-react'
import type { DocumentClassifyResponse, DocumentItem } from '../../services/documentService'
import { classifyDocument, updateDocument, updateDocumentMetadata, startDocumentWorkflow } from '../../services/documentService'
import type { MetadataStructure } from '../../types/metadata'
import { getMetadataStructure } from '../../services/metadataService'

function mapMetadataSuggestionsToFieldNames(
  structure: MetadataStructure | null,
  meta: Record<string, string | undefined>,
): Record<string, unknown> {
  if (!structure?.fields?.length) return {}
  const out: Record<string, unknown> = {}
  const dateVal = meta.date
  const subjectVal = meta.subject
  const protVal = meta.protocol_number
  const amountVal = meta.amount
  const vatVal = meta.vat_number
  const cfVal = meta.fiscal_code

  for (const f of structure.fields) {
    const n = f.name.toLowerCase()
    const l = f.label.toLowerCase()
    if (dateVal && (f.field_type === 'date' || f.field_type === 'datetime')) {
      if (n.includes('data') || l.includes('data') || n.includes('date')) {
        if (!(f.name in out)) out[f.name] = dateVal
      }
    }
    if (
      subjectVal &&
      (n.includes('oggetto') || l.includes('oggetto') || n.includes('subject') || l.includes('subject'))
    ) {
      if (!(f.name in out)) out[f.name] = subjectVal
    }
    if (protVal && (n.includes('protocollo') || l.includes('protocollo') || n.includes('protocol'))) {
      if (!(f.name in out)) out[f.name] = protVal
    }
    if (amountVal && (n.includes('importo') || l.includes('importo') || n.includes('amount'))) {
      if (!(f.name in out)) out[f.name] = amountVal
    }
    if (vatVal && (n.includes('iva') || n.includes('piva') || l.includes('partita'))) {
      if (!(f.name in out)) out[f.name] = vatVal
    }
    if (cfVal && (n.includes('fiscale') || l.includes('fiscale') || n.includes('codice_fiscale'))) {
      if (!(f.name in out)) out[f.name] = cfVal
    }
  }
  return out
}

interface ClassificationSuggestionsProps {
  document: DocumentItem
  onRefresh: () => void
  compact?: boolean
  /** Esegue un'analisi automatica al mount (es. dopo upload e OCR). */
  autoAnalyze?: boolean
}

export function ClassificationSuggestions({
  document: doc,
  onRefresh,
  compact,
  autoAnalyze,
}: ClassificationSuggestionsProps) {
  const [loading, setLoading] = useState(false)
  const [applying, setApplying] = useState(false)
  const [result, setResult] = useState<DocumentClassifyResponse | null>(null)
  const [error, setError] = useState('')

  const analyze = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const data = await classifyDocument(doc.id)
      setResult(data)
    } catch (e: unknown) {
      const msg =
        (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail ||
        (e instanceof Error ? e.message : 'Analisi non riuscita.')
      setError(String(msg))
      setResult(null)
    } finally {
      setLoading(false)
    }
  }, [doc.id])

  const autoRan = useRef(false)
  useEffect(() => {
    if (!autoAnalyze || autoRan.current) return
    autoRan.current = true
    void analyze()
  }, [autoAnalyze, analyze])

  const applyWorkflow = async () => {
    const tid = result?.workflow_template?.id
    if (!tid) return
    try {
      await startDocumentWorkflow(doc.id, tid)
      onRefresh()
    } catch (e: unknown) {
      const msg = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail || 'Errore avvio workflow.'
      setError(String(msg))
    }
  }

  const applySuggestions = async () => {
    if (!result?.metadata_suggestions) return
    setApplying(true)
    setError('')
    try {
      const meta = result.metadata_suggestions
      const subject = meta.subject?.trim()
      const patch: Partial<{ title: string; description: string; metadata_values: Record<string, unknown> }> = {}
      if (subject && !doc.description?.trim()) {
        patch.description = subject
      }
      let structure: MetadataStructure | null = null
      const sid =
        typeof doc.metadata_structure === 'object' && doc.metadata_structure
          ? (doc.metadata_structure as { id: string }).id
          : (doc.metadata_structure as string | undefined)
      if (sid) {
        structure = await getMetadataStructure(sid)
      }
      const mapped = mapMetadataSuggestionsToFieldNames(structure, meta)
      if (Object.keys(mapped).length > 0) {
        const merged = { ...(doc.metadata_values ?? {}), ...mapped }
        await updateDocumentMetadata(doc.id, merged)
      }
      if (Object.keys(patch).length > 0) {
        await updateDocument(doc.id, patch)
      }
      onRefresh()
    } catch (e: unknown) {
      const msg = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail || 'Salvataggio non riuscito.'
      setError(String(msg))
    } finally {
      setApplying(false)
    }
  }

  const metaEntries = result?.metadata_suggestions
    ? Object.entries(result.metadata_suggestions).filter(([, v]) => v != null && String(v).trim() !== '')
    : []

  return (
    <div
      className={`rounded-lg border border-slate-200 bg-slate-50/80 dark:border-slate-600 dark:bg-slate-800/60 ${
        compact ? 'p-3' : 'p-4'
      }`}
    >
      <div className="flex flex-wrap items-center gap-2">
        <button
          type="button"
          onClick={analyze}
          disabled={loading}
          className="inline-flex items-center gap-2 rounded-lg bg-violet-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-violet-700 disabled:opacity-50 dark:bg-violet-700 dark:hover:bg-violet-600"
        >
          <Sparkles className="h-4 w-4" aria-hidden />
          {loading ? 'Analisi…' : 'Analizza documento'}
        </button>
        {result?.suggestions?.length ? (
          <button
            type="button"
            onClick={applySuggestions}
            disabled={applying}
            className="rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-sm font-medium text-slate-800 hover:bg-slate-50 disabled:opacity-50 dark:border-slate-500 dark:bg-slate-700 dark:text-slate-100 dark:hover:bg-slate-600"
          >
            {applying ? 'Applicazione…' : 'Applica suggerimenti'}
          </button>
        ) : null}
      </div>
      {error && <p className="mt-2 text-sm text-red-600 dark:text-red-300">{error}</p>}

      {result?.suggestions && result.suggestions.length > 0 && (
        <div className="mt-4 space-y-3">
          <h4 className="text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">
            Tipo documento suggerito
          </h4>
          <ul className="space-y-2">
            {result.suggestions.map((s) => (
              <li key={s.type} className="text-sm">
                <div className="flex items-center justify-between gap-2">
                  <span className="font-medium text-slate-800 dark:text-slate-100">{s.label}</span>
                  <span className="text-xs text-slate-500 dark:text-slate-400">
                    {Math.round((s.confidence ?? 0) * 100)}% · {s.method}
                  </span>
                </div>
                <div className="mt-1 h-1.5 w-full overflow-hidden rounded-full bg-slate-200 dark:bg-slate-600">
                  <div
                    className="h-full rounded-full bg-violet-500 transition-all dark:bg-violet-400"
                    style={{ width: `${Math.min(100, Math.round((s.confidence ?? 0) * 100))}%` }}
                  />
                </div>
              </li>
            ))}
          </ul>
        </div>
      )}

      {metaEntries.length > 0 && (
        <div className="mt-4">
          <h4 className="text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">
            Metadati estratti
          </h4>
          <dl className="mt-2 grid gap-1 text-sm sm:grid-cols-2">
            {metaEntries.map(([k, v]) => (
              <div key={k} className="flex flex-col rounded border border-slate-100 bg-white px-2 py-1 dark:border-slate-600 dark:bg-slate-900/40">
                <dt className="text-xs text-slate-500 dark:text-slate-400">{k}</dt>
                <dd className="break-all text-slate-800 dark:text-slate-100">{String(v)}</dd>
              </div>
            ))}
          </dl>
        </div>
      )}

      {(result?.workflow_template || result?.workflow_suggestion) && (
        <div className="mt-4 flex flex-wrap items-center gap-2 text-sm">
          <span className="text-slate-600 dark:text-slate-300">
            Workflow suggerito:{' '}
            <strong className="text-slate-800 dark:text-slate-100">
              {result.workflow_template?.name ?? result.workflow_suggestion}
            </strong>
          </span>
          {result.workflow_template?.id && (
            <button
              type="button"
              onClick={applyWorkflow}
              className="rounded bg-indigo-100 px-2 py-1 text-xs font-medium text-indigo-800 hover:bg-indigo-200 dark:bg-indigo-900/50 dark:text-indigo-200 dark:hover:bg-indigo-900/70"
            >
              Applica workflow
            </button>
          )}
        </div>
      )}

      {result?.classification && (
        <p className="mt-2 text-sm text-slate-600 dark:text-slate-300">
          Classificazione titolario:{' '}
          <strong>
            {result.classification.code}
            {result.classification.label ? ` — ${result.classification.label}` : ''}
          </strong>
        </p>
      )}
      {!compact && result?.classification_suggestion && !result?.classification && (
        <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">
          Codice titolario suggerito: {result.classification_suggestion}
        </p>
      )}
    </div>
  )
}
