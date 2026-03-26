import { useState, useEffect } from 'react'
import {
  getWorkflowInstances,
  getPublishedTemplates,
  startWorkflow,
  performStepAction,
  cancelWorkflow,
  type WorkflowInstance,
  type WorkflowTemplate,
} from '../../services/workflowService'
import { useAuthStore } from '../../store/authStore'
import { announce } from '../common/ScreenReaderAnnouncer'

const ACTION_LABELS: Record<string, { label: string; color: string; icon: string }> = {
  review: { label: 'Revisione', color: 'bg-blue-100 text-blue-800', icon: '👁' },
  approve: { label: 'Approvazione', color: 'bg-green-100 text-green-800', icon: '✅' },
  sign: { label: 'Firma', color: 'bg-purple-100 text-purple-800', icon: '✍️' },
  acknowledge: { label: 'Presa visione', color: 'bg-amber-100 text-amber-800', icon: '📋' },
}

const STATUS_LABELS: Record<string, { label: string; color: string }> = {
  pending: { label: 'In attesa', color: 'text-slate-400' },
  in_progress: { label: 'In corso', color: 'text-blue-600 font-semibold' },
  completed: { label: 'Completato', color: 'text-green-600' },
  rejected: { label: 'Rifiutato', color: 'text-red-600' },
  skipped: { label: 'Saltato', color: 'text-slate-400 italic' },
}

const WORKFLOW_STATUS: Record<string, { label: string; color: string }> = {
  active: { label: 'In corso', color: 'bg-blue-100 text-blue-700' },
  completed: { label: 'Completato', color: 'bg-green-100 text-green-700' },
  rejected: { label: 'Rifiutato', color: 'bg-red-100 text-red-700' },
  cancelled: { label: 'Annullato', color: 'bg-slate-100 text-slate-600' },
}

interface WorkflowTabProps {
  documentId: string
}

export function WorkflowTab({ documentId }: WorkflowTabProps) {
  const user = useAuthStore((s) => s.user)
  const [instances, setInstances] = useState<WorkflowInstance[]>([])
  const [templates, setTemplates] = useState<WorkflowTemplate[]>([])
  const [loading, setLoading] = useState(true)
  const [starting, setStarting] = useState(false)
  const [actioning, setActioning] = useState(false)
  const [showStartModal, setShowStartModal] = useState(false)
  const [selectedTemplateId, setSelectedTemplateId] = useState('')
  const [actionComment, setActionComment] = useState('')
  const [showActionModal, setShowActionModal] = useState<{ instanceId: string; stepName: string } | null>(null)

  const loadData = () => {
    setLoading(true)
    Promise.all([
      getWorkflowInstances({ document_id: documentId }).catch(() => ({ results: [] })),
      getPublishedTemplates().catch(() => ({ results: [] })),
    ])
      .then(([inst, tmpl]) => {
        setInstances(inst.results ?? [])
        const raw = tmpl.results ?? []
        setTemplates(raw.filter((t) => t.is_published))
      })
      .finally(() => setLoading(false))
  }

  useEffect(() => {
    loadData()
  }, [documentId])

  const handleStart = async () => {
    if (!selectedTemplateId) return
    setStarting(true)
    try {
      await startWorkflow({ template: selectedTemplateId, document: documentId })
      setShowStartModal(false)
      setSelectedTemplateId('')
      loadData()
    } catch (e: any) {
      alert(e?.response?.data?.detail || 'Errore avvio workflow.')
    } finally {
      setStarting(false)
    }
  }

  const handleAction = async (instanceId: string, action: 'approve' | 'reject' | 'complete') => {
    setActioning(true)
    try {
      await performStepAction(instanceId, {
        action,
        ...(action === 'reject' ? { comment: actionComment } : {}),
      })
      setShowActionModal(null)
      setActionComment('')
      loadData()
      if (action === 'reject') announce('Step rifiutato')
      else announce('Step approvato')
    } catch (e: any) {
      alert(e?.response?.data?.detail || 'Errore.')
    } finally {
      setActioning(false)
    }
  }

  const handleCancel = async (instanceId: string) => {
    if (!confirm('Annullare questo workflow?')) return
    try {
      await cancelWorkflow(instanceId)
      loadData()
    } catch (e: any) {
      alert(e?.response?.data?.detail || 'Errore.')
    }
  }

  const activeInstance = instances.find((i) => i.status === 'active')
  const pastInstances = instances.filter((i) => i.status !== 'active')
  const canStartNew = !activeInstance && templates.length > 0

  if (loading) {
    return <div className="p-4 text-sm text-slate-500">Caricamento workflow...</div>
  }

  return (
    <div className="space-y-4 p-4">
      {/* Pulsante avvia */}
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold text-slate-700">Workflow documentale</h3>
        {canStartNew && (
          <button
            type="button"
            onClick={() => setShowStartModal(true)}
            className="rounded bg-indigo-600 px-3 py-1.5 text-sm text-white hover:bg-indigo-700"
          >
            ▶ Avvia workflow
          </button>
        )}
      </div>

      {/* Nessun workflow */}
      {instances.length === 0 && !canStartNew && (
        <div className="rounded border-2 border-dashed border-slate-200 p-6 text-center">
          <p className="text-sm text-slate-500">Nessun workflow disponibile.</p>
          <p className="text-xs text-slate-400 mt-1">Crea e pubblica un template dal Workflow Builder.</p>
        </div>
      )}

      {instances.length === 0 && canStartNew && (
        <div className="rounded border-2 border-dashed border-slate-200 p-6 text-center">
          <p className="text-sm text-slate-500">Nessun workflow avviato su questo documento.</p>
          <p className="text-xs text-slate-400 mt-1">
            Clicca «Avvia workflow» per iniziare un processo.
          </p>
        </div>
      )}

      {/* Workflow attivo */}
      {activeInstance && (
        <div className="rounded-lg border border-blue-200 bg-blue-50/30">
          <div className="flex items-center justify-between border-b border-blue-200 px-3 py-2">
            <div>
              <span className="text-sm font-semibold text-slate-800">{activeInstance.template_name}</span>
              <span className={`ml-2 rounded px-2 py-0.5 text-xs font-medium ${WORKFLOW_STATUS.active.color}`}>
                {WORKFLOW_STATUS.active.label}
              </span>
            </div>
            <button
              type="button"
              onClick={() => handleCancel(activeInstance.id)}
              className="rounded border border-red-200 px-2 py-1 text-xs text-red-600 hover:bg-red-50"
            >
              Annulla
            </button>
          </div>

          {/* Pipeline step */}
          <div className="p-3 space-y-0">
            {(activeInstance.step_instances ?? []).map((si, i) => {
                const actionInfo = ACTION_LABELS[si.step_action] || { label: si.step_action, color: 'bg-slate-100', icon: '📎' }
                const statusInfo = STATUS_LABELS[si.status] || { label: si.status, color: '' }
                const isCurrentStep = si.status === 'in_progress'
                const isAssignedToMe = (si.assigned_to_emails ?? []).includes(user?.email ?? '')
                const isAdmin = user?.role === 'ADMIN'
                const canAct = isCurrentStep && (isAssignedToMe || isAdmin)

                return (
                  <div key={si.id}>
                    {i > 0 && (
                      <div className="flex justify-center py-0.5">
                        <div className={`h-4 w-0.5 ${si.status === 'pending' ? 'bg-slate-200' : 'bg-slate-300'}`} />
                      </div>
                    )}
                    <div className={`rounded-lg border p-2.5 ${isCurrentStep ? 'border-blue-300 bg-white shadow-sm' : 'border-slate-200'}`}>
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2">
                          <div className={`flex h-6 w-6 shrink-0 items-center justify-center rounded-full text-xs font-bold ${
                            si.status === 'completed' ? 'bg-green-100 text-green-700' :
                            si.status === 'rejected' ? 'bg-red-100 text-red-700' :
                            si.status === 'in_progress' ? 'bg-blue-100 text-blue-700' :
                            si.status === 'skipped' ? 'bg-slate-100 text-slate-400' :
                            'bg-slate-100 text-slate-400'
                          }`}>
                            {si.status === 'completed' ? '✓' : si.status === 'rejected' ? '✗' : si.status === 'skipped' ? '—' : i + 1}
                          </div>
                          <div>
                            <span className="text-sm font-medium text-slate-800">{si.step_name}</span>
                            <span className={`ml-1.5 rounded px-1.5 py-0.5 text-xs ${actionInfo.color}`}>
                              {actionInfo.icon} {actionInfo.label}
                            </span>
                          </div>
                        </div>
                        <span className={`text-xs ${statusInfo.color}`}>{statusInfo.label}</span>
                      </div>

                      {/* Info assegnatari */}
                      {si.assigned_to_emails && si.assigned_to_emails.length > 0 && (
                        <p className="mt-1 ml-8 text-xs text-slate-500">
                          Assegnato a: {si.assigned_to_emails.join(', ')}
                        </p>
                      )}

                      {/* Commento se completato */}
                      {si.comment && si.status !== 'pending' && si.status !== 'in_progress' && (
                        <p className="mt-1 ml-8 text-xs text-slate-500 italic">
                          «{si.comment}»
                        </p>
                      )}

                      {/* Pulsanti azione */}
                      {canAct && (
                        <div className="mt-2 ml-8 flex gap-2">
                          <button
                            type="button"
                            onClick={() => handleAction(activeInstance.id, si.step_action === 'approve' || si.step_action === 'sign' ? 'approve' : 'complete')}
                            disabled={actioning}
                            className="rounded bg-green-600 px-3 py-1 text-xs text-white hover:bg-green-700 disabled:opacity-50"
                          >
                            {si.step_action === 'approve' ? '✅ Approva' : si.step_action === 'sign' ? '✍️ Firma' : si.step_action === 'review' ? '👁 Confermo revisione' : '📋 Confermo'}
                          </button>
                          <button
                            type="button"
                            onClick={() => setShowActionModal({ instanceId: activeInstance.id, stepName: si.step_name })}
                            disabled={actioning}
                            className="rounded border border-red-200 px-3 py-1 text-xs text-red-600 hover:bg-red-50 disabled:opacity-50"
                          >
                            ✗ Rifiuta
                          </button>
                        </div>
                      )}
                    </div>
                  </div>
                )
              })}

            {/* Fine pipeline */}
            <div className="flex justify-center py-0.5">
              <div className="h-4 w-0.5 bg-slate-200" />
            </div>
            <div className="flex justify-center">
              <div className="rounded-full border border-slate-200 bg-slate-50 px-3 py-1 text-xs text-slate-500">
                Fine workflow
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Storico workflow passati */}
      {pastInstances.length > 0 && (
        <div>
          <h4 className="mb-2 text-xs font-semibold uppercase text-slate-500">Storico</h4>
          <div className="space-y-2">
            {pastInstances.map((inst) => {
              const ws = WORKFLOW_STATUS[inst.status] || { label: inst.status, color: 'bg-slate-100 text-slate-600' }
              return (
                <div key={inst.id} className="rounded border border-slate-200 px-3 py-2">
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-slate-700">{inst.template_name}</span>
                    <span className={`rounded px-2 py-0.5 text-xs font-medium ${ws.color}`}>{ws.label}</span>
                  </div>
                  <p className="text-xs text-slate-500 mt-0.5">
                    Avviato {new Date(inst.started_at).toLocaleDateString('it-IT')}
                    {inst.completed_at && ` — Chiuso ${new Date(inst.completed_at).toLocaleDateString('it-IT')}`}
                  </p>
                </div>
              )
            })}
          </div>
        </div>
      )}

      {/* Modal avvia workflow */}
      {showStartModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
          <div className="w-full max-w-sm rounded-lg bg-white p-5 shadow-xl">
            <h3 className="mb-3 text-lg font-semibold text-slate-800">Avvia workflow</h3>
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">Seleziona template</label>
              <select
                value={selectedTemplateId}
                onChange={(e) => setSelectedTemplateId(e.target.value)}
                className="w-full rounded border border-slate-300 px-3 py-2 text-sm"
              >
                <option value="">Scegli un workflow...</option>
                {templates.map((t) => (
                  <option key={t.id} value={t.id}>
                    {t.name} ({t.step_count} step)
                  </option>
                ))}
              </select>
            </div>
            <div className="mt-4 flex justify-end gap-2">
              <button type="button" onClick={() => setShowStartModal(false)} className="rounded bg-slate-200 px-4 py-2 text-sm">
                Annulla
              </button>
              <button
                type="button"
                onClick={handleStart}
                disabled={starting || !selectedTemplateId}
                className="rounded bg-indigo-600 px-4 py-2 text-sm text-white hover:bg-indigo-700 disabled:opacity-50"
              >
                {starting ? 'Avvio...' : '▶ Avvia'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Modal rifiuto con commento */}
      {showActionModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
          <div className="w-full max-w-sm rounded-lg bg-white p-5 shadow-xl">
            <h3 className="mb-3 text-lg font-semibold text-slate-800">Rifiuta step</h3>
            <p className="text-sm text-slate-600 mb-2">Step: {showActionModal.stepName}</p>
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">Motivo del rifiuto</label>
              <textarea
                value={actionComment}
                onChange={(e) => setActionComment(e.target.value)}
                rows={3}
                className="w-full rounded border border-slate-300 px-3 py-2 text-sm"
                placeholder="Spiega il motivo del rifiuto..."
              />
            </div>
            <div className="mt-4 flex justify-end gap-2">
              <button
                type="button"
                onClick={() => { setShowActionModal(null); setActionComment('') }}
                className="rounded bg-slate-200 px-4 py-2 text-sm"
              >
                Annulla
              </button>
              <button
                type="button"
                onClick={() => handleAction(showActionModal.instanceId, 'reject')}
                disabled={actioning}
                className="rounded bg-red-600 px-4 py-2 text-sm text-white hover:bg-red-700 disabled:opacity-50"
              >
                {actioning ? 'Invio...' : 'Rifiuta'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
