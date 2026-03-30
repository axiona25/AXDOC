import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { useAuthStore } from '../store/authStore'
import {
  getWorkflowTemplates,
  getWorkflowTemplate,
  createWorkflowTemplate,
  deleteWorkflowTemplate,
  publishWorkflow,
  unpublishWorkflow,
  createWorkflowStep,
  updateWorkflowStep,
  deleteWorkflowStep,
  type WorkflowTemplate,
  type WorkflowStep,
} from '../services/workflowService'
import { getUsers } from '../services/userService'
import { getOrganizationalUnits, getOUMembers } from '../services/organizationService'
import type { OUMember } from '../services/organizationService'
import type { OrganizationalUnit } from '../services/organizationService'

const ACTION_LABELS: Record<string, { label: string; color: string; icon: string }> = {
  review: { label: 'Revisione', color: 'bg-blue-100 text-blue-800', icon: '👁' },
  approve: { label: 'Approvazione', color: 'bg-green-100 text-green-800', icon: '✅' },
  sign: { label: 'Firma', color: 'bg-purple-100 text-purple-800', icon: '✍️' },
  acknowledge: { label: 'Presa visione', color: 'bg-amber-100 text-amber-800', icon: '📋' },
}

const ASSIGNEE_TYPE_LABELS: Record<string, string> = {
  role: 'Ruolo globale',
  ou_role: 'Ruolo in U.O.',
  specific_user: 'Utente specifico',
  document_ou: 'U.O. del documento',
}

export function WorkflowBuilderPage() {
  const [templates, setTemplates] = useState<WorkflowTemplate[]>([])
  const [loading, setLoading] = useState(true)
  const [selectedTemplate, setSelectedTemplate] = useState<WorkflowTemplate | null>(null)
  const [steps, setSteps] = useState<WorkflowStep[]>([])

  // Create/Edit template
  const [createOpen, setCreateOpen] = useState(false)
  const [editName, setEditName] = useState('')
  const [editDescription, setEditDescription] = useState('')
  const [saving, setSaving] = useState(false)

  // Create/Edit step
  const [stepModalOpen, setStepModalOpen] = useState(false)
  const [editingStep, setEditingStep] = useState<WorkflowStep | null>(null)
  const [stepName, setStepName] = useState('')
  const [stepAction, setStepAction] = useState<string>('review')
  const [stepAssigneeType, setStepAssigneeType] = useState<string>('role')
  const [stepAssigneeRole, setStepAssigneeRole] = useState('')
  const [stepAssigneeUser, setStepAssigneeUser] = useState('')
  const [stepAssigneeOU, setStepAssigneeOU] = useState('')
  const [stepAssigneeOURole, setStepAssigneeOURole] = useState('')
  const [stepRequired, setStepRequired] = useState(true)
  const [stepDeadlineDays, setStepDeadlineDays] = useState<number | ''>('')
  const [stepInstructions, setStepInstructions] = useState('')
  const [stepAccountableUser, setStepAccountableUser] = useState('')
  const [stepConsultedUsers, setStepConsultedUsers] = useState<string[]>([])
  const [stepInformedUsers, setStepInformedUsers] = useState<string[]>([])

  // Risorse
  const [allUsers, setAllUsers] = useState<{ id: string; email: string; first_name?: string; last_name?: string }[]>([])
  const [allOUs, setAllOUs] = useState<OrganizationalUnit[]>([])
  const [ouRolePreview, setOuRolePreview] = useState<OUMember[] | null>(null)
  const [ouRolePreviewLoading, setOuRolePreviewLoading] = useState(false)
  const user = useAuthStore((s) => s.user)

  useEffect(() => {
    loadTemplates()
    getUsers({}).then((r) => setAllUsers(r.results ?? [])).catch(() => {})
    getOrganizationalUnits({}).then((r) => setAllOUs(r.results ?? [])).catch(() => {})
  }, [])

  useEffect(() => {
    if (stepAssigneeType !== 'ou_role' || !stepModalOpen) {
      setOuRolePreview(null)
      return
    }
    if (!stepAssigneeOU || !stepAssigneeOURole) {
      setOuRolePreview(null)
      return
    }
    let cancelled = false
    setOuRolePreviewLoading(true)
    getOUMembers(stepAssigneeOU, { role: stepAssigneeOURole })
      .then((rows) => {
        if (!cancelled) setOuRolePreview(rows ?? [])
      })
      .catch(() => {
        if (!cancelled) setOuRolePreview(null)
      })
      .finally(() => {
        if (!cancelled) setOuRolePreviewLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [stepAssigneeType, stepAssigneeOU, stepAssigneeOURole, stepModalOpen])

  const loadTemplates = () => {
    setLoading(true)
    getWorkflowTemplates().then((r) => setTemplates(r.results ?? [])).catch(() => {}).finally(() => setLoading(false))
  }

  const loadTemplate = async (id: string) => {
    const t = await getWorkflowTemplate(id)
    setSelectedTemplate(t)
    setSteps(t.steps ?? [])
  }

  // Template CRUD
  const handleCreateTemplate = async () => {
    if (!editName.trim()) return
    setSaving(true)
    try {
      const t = await createWorkflowTemplate({ name: editName.trim(), description: editDescription.trim() })
      setCreateOpen(false)
      setEditName('')
      setEditDescription('')
      loadTemplates()
      loadTemplate(t.id)
    } catch { alert('Errore.') }
    finally { setSaving(false) }
  }

  const handleDeleteTemplate = async (id: string) => {
    if (!confirm('Eliminare questo workflow?')) return
    try { await deleteWorkflowTemplate(id); loadTemplates(); if (selectedTemplate?.id === id) setSelectedTemplate(null) }
    catch (e) { alert((e as any)?.response?.data?.detail || 'Errore.') }
  }

  const handlePublish = async () => {
    if (!selectedTemplate) return
    try {
      selectedTemplate.is_published ? await unpublishWorkflow(selectedTemplate.id) : await publishWorkflow(selectedTemplate.id)
      loadTemplate(selectedTemplate.id)
      loadTemplates()
    } catch (e) { alert((e as any)?.response?.data?.detail || 'Errore.') }
  }

  // Step CRUD
  const openStepModal = (step?: WorkflowStep) => {
    if (step) {
      setEditingStep(step)
      setStepName(step.name)
      setStepAction(step.action)
      setStepAssigneeType(step.assignee_type)
      setStepAssigneeRole(step.assignee_role || '')
      setStepAssigneeUser(step.assignee_user || '')
      setStepAssigneeOU(step.assignee_ou || '')
      setStepAssigneeOURole(step.assignee_ou_role || '')
      setStepRequired(step.is_required)
      setStepDeadlineDays(step.deadline_days ?? '')
      setStepInstructions(step.instructions || '')
      setStepAccountableUser(step.accountable_user || '')
      setStepConsultedUsers(step.consulted_users ?? [])
      setStepInformedUsers(step.informed_users ?? [])
    } else {
      setEditingStep(null)
      setStepName('')
      setStepAction('review')
      setStepAssigneeType('role')
      setStepAssigneeRole('APPROVER')
      setStepAssigneeUser('')
      setStepAssigneeOU('')
      setStepAssigneeOURole('')
      setStepRequired(true)
      setStepDeadlineDays('')
      setStepInstructions('')
      setStepAccountableUser('')
      setStepConsultedUsers([])
      setStepInformedUsers([])
    }
    setStepModalOpen(true)
  }

  const handleSaveStep = async () => {
    if (!selectedTemplate || !stepName.trim()) return
    setSaving(true)
    const data: any = {
      name: stepName.trim(),
      action: stepAction,
      assignee_type: stepAssigneeType,
      assignee_role: stepAssigneeType === 'role' ? stepAssigneeRole : (stepAssigneeType === 'ou_role' ? stepAssigneeOURole : null),
      assignee_user: stepAssigneeType === 'specific_user' ? stepAssigneeUser : null,
      assignee_ou: (stepAssigneeType === 'ou_role') ? stepAssigneeOU : null,
      assignee_ou_role: stepAssigneeType === 'ou_role' ? stepAssigneeOURole : null,
      is_required: stepRequired,
      deadline_days: stepDeadlineDays || null,
      instructions: stepInstructions.trim(),
      accountable_user: stepAccountableUser || null,
      consulted_users: stepConsultedUsers,
      informed_users: stepInformedUsers,
    }
    try {
      if (editingStep) {
        await updateWorkflowStep(selectedTemplate.id, editingStep.id, data)
      } else {
        await createWorkflowStep(selectedTemplate.id, data)
      }
      setStepModalOpen(false)
      loadTemplate(selectedTemplate.id)
    } catch (e) { alert((e as any)?.response?.data?.detail || 'Errore.') }
    finally { setSaving(false) }
  }

  const handleDeleteStep = async (stepId: string) => {
    if (!selectedTemplate || !confirm('Eliminare questo step?')) return
    try { await deleteWorkflowStep(selectedTemplate.id, stepId); loadTemplate(selectedTemplate.id) }
    catch { alert('Errore.') }
  }

  return (
    <div className="min-h-screen bg-slate-100 dark:bg-slate-900">
      <header className="border-b border-slate-200 bg-white px-6 py-3 dark:border-slate-700 dark:bg-slate-800">
        <nav className="mb-3 flex flex-wrap items-center gap-3 text-sm">
          <Link to="/dashboard" className="text-indigo-600 hover:underline dark:text-indigo-400">
            Dashboard
          </Link>
          <Link to="/search" className="text-indigo-600 hover:underline dark:text-indigo-400">
            Ricerca
          </Link>
          <Link to="/documents" className="text-indigo-600 hover:underline dark:text-indigo-400">
            Documenti
          </Link>
          <span className="font-semibold text-slate-800 dark:text-slate-100">Workflow</span>
          <Link to="/mail" className="text-indigo-600 hover:underline dark:text-indigo-400">
            Posta
          </Link>
          <Link to="/protocols" className="text-indigo-600 hover:underline dark:text-indigo-400">
            Protocolli
          </Link>
          <Link to="/dossiers" className="text-indigo-600 hover:underline dark:text-indigo-400">
            Fascicoli
          </Link>
          <Link to="/archive" className="text-indigo-600 hover:underline dark:text-indigo-400">
            Archivio
          </Link>
          {user?.role === 'ADMIN' && (
            <>
              <Link to="/metadata" className="text-indigo-600 hover:underline dark:text-indigo-400">
                Metadati
              </Link>
              <Link to="/users" className="text-indigo-600 hover:underline dark:text-indigo-400">
                Utenti
              </Link>
              <Link to="/organizations" className="text-indigo-600 hover:underline dark:text-indigo-400">
                Organizzazioni
              </Link>
              <Link to="/settings" className="text-indigo-600 hover:underline dark:text-indigo-400">
                Impostazioni
              </Link>
              <Link to="/audit" className="text-indigo-600 hover:underline dark:text-indigo-400">
                Audit
              </Link>
            </>
          )}
          <Link to="/profile" className="text-indigo-600 hover:underline dark:text-indigo-400">
            Profilo
          </Link>
        </nav>
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-xl font-bold text-slate-800 dark:text-slate-100">Workflow Builder</h1>
            <p className="text-sm text-slate-500 dark:text-slate-400">
              Crea processi di approvazione, firma e revisione documentale
            </p>
          </div>
          <button
            type="button"
            onClick={() => setCreateOpen(true)}
            className="rounded bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 dark:hover:bg-indigo-500"
          >
            + Nuovo workflow
          </button>
        </div>
      </header>

      <div className="p-6">
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
          {/* LISTA TEMPLATE */}
          <div className="lg:col-span-1">
            <div className="rounded-lg border border-slate-200 bg-white dark:border-slate-700 dark:bg-slate-800">
              <div className="border-b border-slate-200 px-4 py-3 dark:border-slate-600">
                <h2 className="font-semibold text-slate-800 dark:text-slate-100">Template workflow</h2>
              </div>
              <div className="max-h-[70vh] divide-y divide-slate-100 overflow-y-auto dark:divide-slate-700">
                {loading ? (
                  <p className="p-4 text-sm text-slate-500 dark:text-slate-400">Caricamento...</p>
                ) : templates.length === 0 ? (
                  <p className="p-4 text-sm text-slate-500">Nessun workflow. Creane uno nuovo.</p>
                ) : templates.map((t) => (
                  <button
                    key={t.id}
                    type="button"
                    onClick={() => loadTemplate(t.id)}
                    className={`flex w-full items-center justify-between px-4 py-3 text-left hover:bg-slate-50 ${selectedTemplate?.id === t.id ? 'bg-indigo-50' : ''}`}
                  >
                    <div>
                      <p className="text-sm font-medium text-slate-800">{t.name}</p>
                      <p className="text-xs text-slate-500">{t.step_count} step</p>
                    </div>
                    <span className={`rounded px-2 py-0.5 text-xs font-medium ${t.is_published ? 'bg-green-100 text-green-700' : 'bg-slate-100 text-slate-500'}`}>
                      {t.is_published ? 'Pubblicato' : 'Bozza'}
                    </span>
                  </button>
                ))}
              </div>
            </div>
          </div>

          {/* DETTAGLIO + STEP BUILDER */}
          <div className="lg:col-span-2">
            {selectedTemplate ? (
              <div className="rounded-lg border border-slate-200 bg-white dark:border-slate-700 dark:bg-slate-800">
                {/* Header template */}
                <div className="border-b border-slate-200 px-4 py-3">
                  <div className="flex items-center justify-between">
                    <div>
                      <h2 className="text-lg font-semibold text-slate-800">{selectedTemplate.name}</h2>
                      {selectedTemplate.description && <p className="text-sm text-slate-500">{selectedTemplate.description}</p>}
                    </div>
                    <div className="flex gap-2">
                      <button type="button" onClick={handlePublish} className={`rounded px-3 py-1.5 text-sm font-medium ${selectedTemplate.is_published ? 'bg-amber-100 text-amber-700 hover:bg-amber-200' : 'bg-green-100 text-green-700 hover:bg-green-200'}`}>
                        {selectedTemplate.is_published ? 'Sospendi pubblicazione' : 'Pubblica'}
                      </button>
                      <button type="button" onClick={() => handleDeleteTemplate(selectedTemplate.id)} className="rounded border border-red-200 px-3 py-1.5 text-sm text-red-600 hover:bg-red-50">
                        Elimina
                      </button>
                    </div>
                  </div>
                </div>

                {/* Step pipeline visuale */}
                <div className="p-4">
                  <div className="flex items-center justify-between mb-4">
                    <h3 className="font-medium text-slate-700">Pipeline step</h3>
                    {!selectedTemplate.is_published && (
                      <button type="button" onClick={() => openStepModal()} className="rounded bg-indigo-600 px-3 py-1.5 text-sm text-white hover:bg-indigo-700">
                        + Aggiungi step
                      </button>
                    )}
                  </div>

                  {steps.length === 0 ? (
                    <div className="rounded border-2 border-dashed border-slate-300 p-8 text-center">
                      <p className="text-slate-500">Nessuno step definito.</p>
                      <p className="text-sm text-slate-400 mt-1">Aggiungi step per costruire il flusso di lavoro.</p>
                    </div>
                  ) : (
                    <div className="space-y-0">
                      {steps.map((step, i) => {
                        const actionInfo = ACTION_LABELS[step.action] || { label: step.action, color: 'bg-slate-100 text-slate-700', icon: '📎' }
                        return (
                          <div key={step.id}>
                            {/* Connettore */}
                            {i > 0 && (
                              <div className="flex justify-center py-1">
                                <div className="h-6 w-0.5 bg-slate-300"></div>
                              </div>
                            )}
                            {/* Step card */}
                            <div className="rounded-lg border border-slate-200 p-3 hover:shadow-sm transition-shadow">
                              <div className="flex items-start justify-between">
                                <div className="flex items-start gap-3">
                                  <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-indigo-100 text-sm font-bold text-indigo-700">
                                    {i + 1}
                                  </div>
                                  <div>
                                    <p className="text-sm font-semibold text-slate-800">{step.name}</p>
                                    <div className="mt-1 flex flex-wrap gap-1.5">
                                      <span className={`rounded px-2 py-0.5 text-xs font-medium ${actionInfo.color}`}>
                                        {actionInfo.icon} {actionInfo.label}
                                      </span>
                                      <span className="rounded bg-slate-100 px-2 py-0.5 text-xs text-slate-600">
                                        {step.assignee_display}
                                      </span>
                                      {step.deadline_days && (
                                        <span className="rounded bg-orange-50 px-2 py-0.5 text-xs text-orange-600">
                                          ⏱ {step.deadline_days}g
                                        </span>
                                      )}
                                      {!step.is_required && (
                                        <span className="rounded bg-slate-50 px-2 py-0.5 text-xs text-slate-400 italic">
                                          Facoltativo
                                        </span>
                                      )}
                                      {step.accountable_user_display && (
                                        <span className="rounded bg-indigo-50 px-2 py-0.5 text-xs text-indigo-600">
                                          A: {step.accountable_user_display}
                                        </span>
                                      )}
                                      {step.consulted_users_display && step.consulted_users_display.length > 0 && (
                                        <span className="rounded bg-cyan-50 px-2 py-0.5 text-xs text-cyan-600">
                                          C: {step.consulted_users_display.length}
                                        </span>
                                      )}
                                      {step.informed_users_display && step.informed_users_display.length > 0 && (
                                        <span className="rounded bg-slate-100 px-2 py-0.5 text-xs text-slate-500">
                                          I: {step.informed_users_display.length}
                                        </span>
                                      )}
                                    </div>
                                    {step.instructions && (
                                      <p className="mt-1 text-xs text-slate-500">{step.instructions}</p>
                                    )}
                                  </div>
                                </div>
                                {!selectedTemplate.is_published && (
                                  <div className="flex gap-1 shrink-0">
                                    <button type="button" onClick={() => openStepModal(step)} className="rounded p-1 text-slate-400 hover:bg-slate-100 hover:text-slate-600" title="Modifica">✏️</button>
                                    <button type="button" onClick={() => handleDeleteStep(step.id)} className="rounded p-1 text-slate-400 hover:bg-red-50 hover:text-red-600" title="Elimina">🗑</button>
                                  </div>
                                )}
                              </div>
                            </div>
                          </div>
                        )
                      })}
                      {/* Fine pipeline */}
                      <div className="flex justify-center py-1">
                        <div className="h-6 w-0.5 bg-slate-300"></div>
                      </div>
                      <div className="flex justify-center">
                        <div className="rounded-full border-2 border-green-400 bg-green-50 px-4 py-1.5 text-sm font-medium text-green-700">
                          ✅ Workflow completato
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              </div>
            ) : (
              <div className="rounded-lg border border-slate-200 bg-white dark:border-slate-700 dark:bg-slate-800 p-8 text-center text-slate-500">
                <p className="text-lg">Seleziona un template o creane uno nuovo</p>
                <p className="text-sm mt-1">Il workflow builder ti permette di definire processi di approvazione, firma e revisione.</p>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Modal crea template */}
      {createOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
          <div className="w-full max-w-md rounded-lg bg-white p-6 shadow-xl">
            <h2 className="mb-4 text-lg font-semibold text-slate-800">Nuovo workflow</h2>
            <div className="space-y-3">
              <div>
                <label className="block text-sm font-medium text-slate-700">Nome *</label>
                <input type="text" value={editName} onChange={(e) => setEditName(e.target.value)} className="mt-1 w-full rounded border border-slate-300 px-3 py-2 text-sm" placeholder="es. Approvazione fatture" />
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-700">Descrizione</label>
                <textarea value={editDescription} onChange={(e) => setEditDescription(e.target.value)} rows={2} className="mt-1 w-full rounded border border-slate-300 px-3 py-2 text-sm" />
              </div>
            </div>
            <div className="mt-4 flex justify-end gap-2">
              <button type="button" onClick={() => setCreateOpen(false)} className="rounded bg-slate-200 px-4 py-2 text-sm">Annulla</button>
              <button type="button" onClick={handleCreateTemplate} disabled={saving || !editName.trim()} className="rounded bg-indigo-600 px-4 py-2 text-sm text-white hover:bg-indigo-700 disabled:opacity-50">
                {saving ? 'Creazione...' : 'Crea'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Modal step */}
      {stepModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
          <div className="w-full max-w-lg rounded-lg bg-white p-6 shadow-xl max-h-[85vh] overflow-y-auto">
            <h2 className="mb-4 text-lg font-semibold text-slate-800">{editingStep ? 'Modifica step' : 'Nuovo step'}</h2>
            <div className="space-y-3">
              <div>
                <label className="block text-sm font-medium text-slate-700">Nome step *</label>
                <input type="text" value={stepName} onChange={(e) => setStepName(e.target.value)} className="mt-1 w-full rounded border border-slate-300 px-3 py-2 text-sm" placeholder="es. Revisione responsabile" />
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Azione *</label>
                <div className="grid grid-cols-2 gap-2">
                  {Object.entries(ACTION_LABELS).map(([key, info]) => (
                    <button key={key} type="button" onClick={() => setStepAction(key)}
                      className={`rounded border px-3 py-2 text-sm text-left ${stepAction === key ? 'border-indigo-500 bg-indigo-50' : 'border-slate-300 hover:bg-slate-50'}`}>
                      {info.icon} {info.label}
                    </button>
                  ))}
                </div>
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Assegnatario *</label>
                <select value={stepAssigneeType} onChange={(e) => setStepAssigneeType(e.target.value)} className="w-full rounded border border-slate-300 px-3 py-2 text-sm">
                  {Object.entries(ASSIGNEE_TYPE_LABELS).map(([v, l]) => (<option key={v} value={v}>{l}</option>))}
                </select>
              </div>
              {stepAssigneeType === 'role' && (
                <div>
                  <label className="block text-sm font-medium text-slate-700">Ruolo</label>
                  <select value={stepAssigneeRole} onChange={(e) => setStepAssigneeRole(e.target.value)} className="mt-1 w-full rounded border border-slate-300 px-3 py-2 text-sm">
                    <option value="OPERATOR">Operatore</option>
                    <option value="REVIEWER">Revisore</option>
                    <option value="APPROVER">Approvatore</option>
                    <option value="ADMIN">Amministratore</option>
                  </select>
                </div>
              )}
              {stepAssigneeType === 'specific_user' && (
                <div>
                  <label className="block text-sm font-medium text-slate-700">Utente</label>
                  <select value={stepAssigneeUser} onChange={(e) => setStepAssigneeUser(e.target.value)} className="mt-1 w-full rounded border border-slate-300 px-3 py-2 text-sm">
                    <option value="">Seleziona...</option>
                    {allUsers.map((u) => (<option key={u.id} value={u.id}>{u.first_name} {u.last_name} ({u.email})</option>))}
                  </select>
                </div>
              )}
              {stepAssigneeType === 'ou_role' && (
                <>
                  <div>
                    <label className="block text-sm font-medium text-slate-700">Unità Organizzativa</label>
                    <select value={stepAssigneeOU} onChange={(e) => setStepAssigneeOU(e.target.value)} className="mt-1 w-full rounded border border-slate-300 px-3 py-2 text-sm">
                      <option value="">Seleziona...</option>
                      {allOUs.map((ou) => (<option key={ou.id} value={ou.id}>{ou.name} ({ou.code})</option>))}
                    </select>
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-slate-700">Ruolo nella U.O.</label>
                    <select value={stepAssigneeOURole} onChange={(e) => setStepAssigneeOURole(e.target.value)} className="mt-1 w-full rounded border border-slate-300 px-3 py-2 text-sm">
                      <option value="OPERATOR">Operatore</option>
                      <option value="REVIEWER">Revisore</option>
                      <option value="APPROVER">Approvatore</option>
                    </select>
                  </div>
                  {stepAssigneeOU && stepAssigneeOURole && (
                    <div className="rounded border border-slate-200 bg-slate-50 p-3 text-sm">
                      {ouRolePreviewLoading && <p className="text-slate-500">Verifica membri…</p>}
                      {!ouRolePreviewLoading && ouRolePreview && ouRolePreview.length === 0 && (
                        <p className="font-medium text-red-700">
                          Nessun utente con ruolo {stepAssigneeOURole} nella UO{' '}
                          {allOUs.find((o) => o.id === stepAssigneeOU)?.name ?? stepAssigneeOU}
                        </p>
                      )}
                      {!ouRolePreviewLoading && ouRolePreview && ouRolePreview.length > 0 && (
                        <>
                          <p className="mb-2 text-slate-600">
                            {ouRolePreview.length} utente{ouRolePreview.length === 1 ? '' : 'i'} con ruolo{' '}
                            {stepAssigneeOURole} in questa UO:
                          </p>
                          <ul className="max-h-40 list-inside list-disc space-y-0.5 overflow-y-auto text-slate-800">
                            {ouRolePreview.map((m) => (
                              <li key={m.id}>
                                {m.user_name || m.user_email} ({m.user_email})
                              </li>
                            ))}
                          </ul>
                        </>
                      )}
                    </div>
                  )}
                </>
              )}
              <div>
                <label className="block text-sm font-medium text-slate-700">Scadenza (giorni)</label>
                <input type="number" min="1" value={stepDeadlineDays} onChange={(e) => setStepDeadlineDays(e.target.value ? parseInt(e.target.value) : '')} className="mt-1 w-full rounded border border-slate-300 px-3 py-2 text-sm" placeholder="es. 5" />
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-700">Istruzioni</label>
                <textarea value={stepInstructions} onChange={(e) => setStepInstructions(e.target.value)} rows={2} className="mt-1 w-full rounded border border-slate-300 px-3 py-2 text-sm" placeholder="Istruzioni per chi esegue lo step..." />
              </div>
              <div className="border-t border-slate-200 pt-3 mt-1">
                <p className="text-xs font-semibold text-slate-500 uppercase mb-2">Matrice RACI</p>
                <p className="text-xs text-slate-400 mb-3">
                  R = chi esegue (già definito sopra) · A = supervisore · C = da consultare · I = da informare
                </p>
                <div className="mb-2">
                  <label className="block text-sm font-medium text-slate-700">Supervisore (A)</label>
                  <select
                    value={stepAccountableUser}
                    onChange={(e) => setStepAccountableUser(e.target.value)}
                    className="mt-1 w-full rounded border border-slate-300 px-3 py-2 text-sm"
                  >
                    <option value="">Nessuno</option>
                    {allUsers.map((u) => (
                      <option key={u.id} value={u.id}>
                        {u.first_name} {u.last_name} ({u.email})
                      </option>
                    ))}
                  </select>
                </div>
                <div className="mb-2">
                  <label className="block text-sm font-medium text-slate-700">Da consultare (C)</label>
                  <select
                    multiple
                    value={stepConsultedUsers}
                    onChange={(e) => setStepConsultedUsers(Array.from(e.target.selectedOptions, (o) => o.value))}
                    className="mt-1 w-full rounded border border-slate-300 px-3 py-2 text-sm"
                    size={3}
                  >
                    {allUsers.map((u) => (
                      <option key={u.id} value={u.id}>
                        {u.first_name} {u.last_name} ({u.email})
                      </option>
                    ))}
                  </select>
                  <p className="text-xs text-slate-400 mt-0.5">Tieni premuto Cmd/Ctrl per selezione multipla</p>
                </div>
                <div className="mb-2">
                  <label className="block text-sm font-medium text-slate-700">Da informare (I)</label>
                  <select
                    multiple
                    value={stepInformedUsers}
                    onChange={(e) => setStepInformedUsers(Array.from(e.target.selectedOptions, (o) => o.value))}
                    className="mt-1 w-full rounded border border-slate-300 px-3 py-2 text-sm"
                    size={3}
                  >
                    {allUsers.map((u) => (
                      <option key={u.id} value={u.id}>
                        {u.first_name} {u.last_name} ({u.email})
                      </option>
                    ))}
                  </select>
                  <p className="text-xs text-slate-400 mt-0.5">Tieni premuto Cmd/Ctrl per selezione multipla</p>
                </div>
              </div>
              <label className="flex items-center gap-2 cursor-pointer">
                <input type="checkbox" checked={stepRequired} onChange={(e) => setStepRequired(e.target.checked)} className="rounded" />
                <span className="text-sm text-slate-700">Step obbligatorio</span>
              </label>
            </div>
            <div className="mt-4 flex justify-end gap-2">
              <button type="button" onClick={() => setStepModalOpen(false)} className="rounded bg-slate-200 px-4 py-2 text-sm">Annulla</button>
              <button type="button" onClick={handleSaveStep} disabled={saving || !stepName.trim()} className="rounded bg-indigo-600 px-4 py-2 text-sm text-white hover:bg-indigo-700 disabled:opacity-50">
                {saving ? 'Salvataggio...' : editingStep ? 'Salva' : 'Aggiungi step'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
