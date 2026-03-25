import { useEffect, useId, useState } from 'react'
import { useFocusTrap } from '../../hooks/useFocusTrap'
import type { SecurityIncident, SecurityIncidentPayload } from '../../services/securityService'

interface IncidentFormModalProps {
  open: boolean
  initial?: SecurityIncident | null
  onClose: () => void
  onSave: (payload: SecurityIncidentPayload) => Promise<void>
}

const emptyPayload: SecurityIncidentPayload = {
  title: '',
  description: '',
  severity: 'low',
  status: 'open',
  category: 'other',
  affected_systems: '',
  affected_users_count: 0,
  data_compromised: false,
  containment_actions: '',
  remediation_actions: '',
  reported_to_authority: false,
  authority_report_date: null,
  authority_reference: '',
  assigned_to: null,
  detected_at: new Date().toISOString().slice(0, 16),
}

export function IncidentFormModal({ open, initial, onClose, onSave }: IncidentFormModalProps) {
  const titleId = useId()
  const trapRef = useFocusTrap(open)
  const [form, setForm] = useState<SecurityIncidentPayload>(emptyPayload)
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    if (!open) return
    if (initial) {
      setForm({
        title: initial.title,
        description: initial.description,
        severity: initial.severity,
        status: initial.status,
        category: initial.category,
        affected_systems: initial.affected_systems,
        affected_users_count: initial.affected_users_count,
        data_compromised: initial.data_compromised,
        containment_actions: initial.containment_actions,
        remediation_actions: initial.remediation_actions,
        reported_to_authority: initial.reported_to_authority,
        authority_report_date: initial.authority_report_date,
        authority_reference: initial.authority_reference,
        assigned_to: initial.assigned_to,
        detected_at: initial.detected_at.slice(0, 16),
      })
    } else {
      setForm({
        ...emptyPayload,
        detected_at: new Date().toISOString().slice(0, 16),
      })
    }
  }, [open, initial])

  useEffect(() => {
    if (!open) return
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        e.preventDefault()
        onClose()
      }
    }
    document.addEventListener('keydown', onKey)
    return () => document.removeEventListener('keydown', onKey)
  }, [open, onClose])

  if (!open) return null

  const set = (k: keyof SecurityIncidentPayload, v: unknown) =>
    setForm((f) => ({ ...f, [k]: v }))

  const submit = async (e: React.FormEvent) => {
    e.preventDefault()
    setSaving(true)
    try {
      const payload = {
        ...form,
        detected_at: new Date(form.detected_at).toISOString(),
        authority_report_date: form.authority_report_date
          ? new Date(form.authority_report_date).toISOString()
          : null,
      }
      await onSave(payload)
      onClose()
    } finally {
      setSaving(false)
    }
  }

  const field =
    'w-full rounded border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 dark:border-slate-600 dark:bg-slate-700 dark:text-slate-100'

  return (
    <div
      className="fixed inset-0 z-[70] flex items-center justify-center bg-black/50 p-4"
      role="presentation"
      onMouseDown={(e) => {
        if (e.target === e.currentTarget) onClose()
      }}
    >
      <div
        ref={trapRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        className="max-h-[90vh] w-full max-w-lg overflow-y-auto rounded-lg border border-slate-200 bg-white p-5 shadow-xl dark:border-slate-600 dark:bg-slate-800"
      >
        <h2 id={titleId} className="text-lg font-semibold text-slate-900 dark:text-slate-100">
          {initial ? 'Modifica incidente' : 'Nuovo incidente'}
        </h2>
        <form onSubmit={(e) => void submit(e)} className="mt-4 space-y-3">
          <div>
            <label htmlFor="inc-title" className="mb-1 block text-xs font-medium text-slate-600 dark:text-slate-300">
              Titolo *
            </label>
            <input
              id="inc-title"
              required
              value={form.title}
              onChange={(e) => set('title', e.target.value)}
              className={field}
            />
          </div>
          <div>
            <label htmlFor="inc-desc" className="mb-1 block text-xs font-medium text-slate-600 dark:text-slate-300">
              Descrizione *
            </label>
            <textarea
              id="inc-desc"
              required
              rows={3}
              value={form.description}
              onChange={(e) => set('description', e.target.value)}
              className={field}
            />
          </div>
          <div className="grid gap-3 sm:grid-cols-2">
            <div>
              <label htmlFor="inc-sev" className="mb-1 block text-xs font-medium text-slate-600 dark:text-slate-300">
                Severità *
              </label>
              <select
                id="inc-sev"
                value={form.severity}
                onChange={(e) => set('severity', e.target.value)}
                className={field}
              >
                <option value="low">Basso</option>
                <option value="medium">Medio</option>
                <option value="high">Alto</option>
                <option value="critical">Critico</option>
              </select>
            </div>
            <div>
              <label htmlFor="inc-cat" className="mb-1 block text-xs font-medium text-slate-600 dark:text-slate-300">
                Categoria *
              </label>
              <select
                id="inc-cat"
                value={form.category}
                onChange={(e) => set('category', e.target.value)}
                className={field}
              >
                <option value="unauthorized_access">Accesso non autorizzato</option>
                <option value="data_breach">Violazione dati</option>
                <option value="malware">Malware</option>
                <option value="phishing">Phishing</option>
                <option value="dos">DoS</option>
                <option value="misconfiguration">Configurazione</option>
                <option value="other">Altro</option>
              </select>
            </div>
          </div>
          <div>
            <label htmlFor="inc-detected" className="mb-1 block text-xs font-medium text-slate-600 dark:text-slate-300">
              Rilevato il *
            </label>
            <input
              id="inc-detected"
              type="datetime-local"
              required
              value={form.detected_at}
              onChange={(e) => set('detected_at', e.target.value)}
              className={field}
            />
          </div>
          <div>
            <label htmlFor="inc-sys" className="mb-1 block text-xs font-medium text-slate-600 dark:text-slate-300">
              Sistemi coinvolti
            </label>
            <textarea
              id="inc-sys"
              rows={2}
              value={form.affected_systems}
              onChange={(e) => set('affected_systems', e.target.value)}
              className={field}
            />
          </div>
          <div>
            <label htmlFor="inc-users" className="mb-1 block text-xs font-medium text-slate-600 dark:text-slate-300">
              Utenti coinvolti (numero)
            </label>
            <input
              id="inc-users"
              type="number"
              min={0}
              value={form.affected_users_count}
              onChange={(e) => set('affected_users_count', parseInt(e.target.value, 10) || 0)}
              className={field}
            />
          </div>
          <div className="flex gap-2">
            <input
              id="inc-breach"
              type="checkbox"
              checked={form.data_compromised}
              onChange={(e) => set('data_compromised', e.target.checked)}
            />
            <label htmlFor="inc-breach" className="text-sm text-slate-700 dark:text-slate-200">
              Dati compromessi
            </label>
          </div>
          <div>
            <label htmlFor="inc-cont" className="mb-1 block text-xs font-medium text-slate-600 dark:text-slate-300">
              Contenimento
            </label>
            <textarea
              id="inc-cont"
              rows={2}
              value={form.containment_actions}
              onChange={(e) => set('containment_actions', e.target.value)}
              className={field}
            />
          </div>
          <div>
            <label htmlFor="inc-rem" className="mb-1 block text-xs font-medium text-slate-600 dark:text-slate-300">
              Rimedio
            </label>
            <textarea
              id="inc-rem"
              rows={2}
              value={form.remediation_actions}
              onChange={(e) => set('remediation_actions', e.target.value)}
              className={field}
            />
          </div>
          <div className="flex flex-wrap gap-4">
            <div className="flex gap-2">
              <input
                id="inc-auth"
                type="checkbox"
                checked={form.reported_to_authority}
                onChange={(e) => set('reported_to_authority', e.target.checked)}
              />
              <label htmlFor="inc-auth" className="text-sm text-slate-700 dark:text-slate-200">
                Segnalato all&apos;autorità
              </label>
            </div>
          </div>
          {form.reported_to_authority && (
            <>
              <div>
                <label htmlFor="inc-adate" className="mb-1 block text-xs font-medium text-slate-600 dark:text-slate-300">
                  Data segnalazione
                </label>
                <input
                  id="inc-adate"
                  type="datetime-local"
                  value={
                    form.authority_report_date
                      ? form.authority_report_date.slice(0, 16)
                      : ''
                  }
                  onChange={(e) =>
                    set(
                      'authority_report_date',
                      e.target.value ? new Date(e.target.value).toISOString() : null,
                    )
                  }
                  className={field}
                />
              </div>
              <div>
                <label htmlFor="inc-aref" className="mb-1 block text-xs font-medium text-slate-600 dark:text-slate-300">
                  Riferimento autorità
                </label>
                <input
                  id="inc-aref"
                  value={form.authority_reference}
                  onChange={(e) => set('authority_reference', e.target.value)}
                  className={field}
                />
              </div>
            </>
          )}
          {initial && (
            <div>
              <label htmlFor="inc-status" className="mb-1 block text-xs font-medium text-slate-600 dark:text-slate-300">
                Stato
              </label>
              <select
                id="inc-status"
                value={form.status}
                onChange={(e) => set('status', e.target.value)}
                className={field}
              >
                <option value="open">Aperto</option>
                <option value="investigating">In indagine</option>
                <option value="mitigated">Mitigato</option>
                <option value="resolved">Risolto</option>
                <option value="closed">Chiuso</option>
              </select>
            </div>
          )}
          <div className="flex justify-end gap-2 pt-2">
            <button
              type="button"
              onClick={onClose}
              className="rounded border border-slate-300 px-4 py-2 text-sm dark:border-slate-500 dark:text-slate-200"
            >
              Annulla
            </button>
            <button
              type="submit"
              disabled={saving}
              className="rounded bg-indigo-600 px-4 py-2 text-sm text-white hover:bg-indigo-700 disabled:opacity-50 dark:hover:bg-indigo-500"
            >
              {saving ? 'Salvataggio…' : 'Salva'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
