import { useState, useCallback, useId } from 'react'
import { Dialog, DialogTitle } from '@headlessui/react'
import { useFocusTrap } from '../../hooks/useFocusTrap'
import { useModalEscape } from '../../hooks/useModalAccessibility'
import {
  downloadImportTemplate,
  importPreview,
  importUsers,
  type ImportPreviewRow,
  type ImportResult,
} from '../../services/userService'

interface ImportUsersModalProps {
  isOpen: boolean
  onClose: () => void
  onSuccess: () => void
}

type Step = 'upload' | 'preview' | 'results'

export function ImportUsersModal({ isOpen, onClose, onSuccess }: ImportUsersModalProps) {
  const titleId = useId()
  const trapRef = useFocusTrap(isOpen)
  const [step, setStep] = useState<Step>('upload')
  const [file, setFile] = useState<File | null>(null)
  const [preview, setPreview] = useState<ImportPreviewRow[]>([])
  const [validCount, setValidCount] = useState(0)
  const [invalidCount, setInvalidCount] = useState(0)
  const [sendInvite, setSendInvite] = useState(true)
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<ImportResult | null>(null)
  const [error, setError] = useState<string | null>(null)

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0]
    if (f && (f.name.endsWith('.csv') || f.name.endsWith('.xlsx'))) {
      setFile(f)
      setError(null)
    } else if (f) {
      setError('Usa un file .csv o .xlsx')
    }
  }

  const handlePreview = async () => {
    if (!file) return
    setLoading(true)
    setError(null)
    try {
      const data = await importPreview(file)
      setPreview(data.preview)
      setValidCount(data.valid_rows)
      setInvalidCount(data.invalid_rows)
      setStep('preview')
    } catch {
      setError('Errore durante l\'anteprima del file')
    } finally {
      setLoading(false)
    }
  }

  const handleImport = async () => {
    if (!file) return
    setLoading(true)
    setError(null)
    try {
      const data = await importUsers(file, sendInvite)
      setResult(data)
      setStep('results')
      onSuccess()
    } catch {
      setError('Errore durante l\'importazione')
    } finally {
      setLoading(false)
    }
  }

  const handleClose = useCallback(() => {
    setStep('upload')
    setFile(null)
    setPreview([])
    setResult(null)
    setError(null)
    onClose()
  }, [onClose])

  const downloadTemplate = (format: 'csv' | 'xlsx') => {
    downloadImportTemplate(format).catch(() => setError('Errore download template'))
  }

  useModalEscape(isOpen, handleClose)

  if (!isOpen) return null

  return (
    <Dialog open={isOpen} onClose={handleClose} className="relative z-50">
      <div
        className="fixed inset-0 bg-black/30"
        aria-hidden="true"
        role="presentation"
        onMouseDown={(e) => {
          if (e.target === e.currentTarget) handleClose()
        }}
      />
      <div className="fixed inset-0 flex items-center justify-center p-4">
        <Dialog.Panel
          ref={trapRef}
          role="dialog"
          aria-modal="true"
          aria-labelledby={titleId}
          className="mx-auto max-h-[90vh] w-full max-w-2xl overflow-y-auto rounded-lg bg-white p-6 shadow-xl"
        >
          <DialogTitle id={titleId} className="text-lg font-semibold text-slate-800">
            Importa utenti
          </DialogTitle>

          {step === 'upload' && (
            <>
              <p className="mt-2 text-sm text-slate-600">
                Scarica il template e carica un file CSV o Excel con le colonne: email, first_name, last_name, role, organizational_unit_code, ou_role, phone.
              </p>
              <div className="mt-4 flex gap-2">
                <button
                  type="button"
                  onClick={() => downloadTemplate('csv')}
                  className="rounded border border-slate-300 px-3 py-1.5 text-sm text-slate-700 hover:bg-slate-50"
                >
                  Scarica CSV
                </button>
                <button
                  type="button"
                  onClick={() => downloadTemplate('xlsx')}
                  className="rounded border border-slate-300 px-3 py-1.5 text-sm text-slate-700 hover:bg-slate-50"
                >
                  Scarica Excel
                </button>
              </div>
              <div className="mt-4">
                <label className="block text-sm font-medium text-slate-700">Carica file</label>
                <input
                  type="file"
                  accept=".csv,.xlsx"
                  onChange={handleFileChange}
                  className="mt-1 block w-full text-sm text-slate-600 file:mr-4 file:rounded file:border-0 file:bg-indigo-50 file:px-4 file:py-2 file:text-indigo-700"
                />
                {file && <p className="mt-1 text-xs text-slate-500">{file.name}</p>}
              </div>
              {error && <p className="mt-2 text-sm text-red-600">{error}</p>}
              <div className="mt-6 flex justify-end gap-2">
                <button type="button" onClick={handleClose} className="rounded border border-slate-300 px-4 py-2 text-slate-700 hover:bg-slate-50">
                  Annulla
                </button>
                <button
                  type="button"
                  onClick={handlePreview}
                  disabled={!file || loading}
                  className="rounded bg-indigo-600 px-4 py-2 text-white hover:bg-indigo-700 disabled:opacity-50"
                >
                  {loading ? 'Caricamento...' : 'Anteprima'}
                </button>
              </div>
            </>
          )}

          {step === 'preview' && (
            <>
              <p className="mt-2 text-sm text-slate-600">
                Righe valide: {validCount} — Con errori: {invalidCount}
              </p>
              <div className="mt-3 max-h-60 overflow-y-auto rounded border border-slate-200">
                <table className="min-w-full text-sm">
                  <thead className="bg-slate-50">
                    <tr>
                      <th className="px-2 py-1 text-left">Riga</th>
                      <th className="px-2 py-1 text-left">Email</th>
                      <th className="px-2 py-1 text-left">Nome</th>
                      <th className="px-2 py-1 text-left">Stato</th>
                    </tr>
                  </thead>
                  <tbody>
                    {preview.map((row) => (
                      <tr key={row.row} className="border-t border-slate-100">
                        <td className="px-2 py-1">{row.row}</td>
                        <td className="px-2 py-1">{row.email}</td>
                        <td className="px-2 py-1">{row.name}</td>
                        <td className="px-2 py-1">
                          {row.valid ? (
                            <span className="text-green-600">✓</span>
                          ) : (
                            <span className="text-red-600" title={row.errors.join(', ')}>✗ {row.errors[0]}</span>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <label className="mt-4 flex items-center gap-2">
                <input
                  type="checkbox"
                  checked={sendInvite}
                  onChange={(e) => setSendInvite(e.target.checked)}
                  className="rounded border-slate-300"
                />
                <span className="text-sm text-slate-700">Invia email di invito agli utenti creati</span>
              </label>
              {error && <p className="mt-2 text-sm text-red-600">{error}</p>}
              <div className="mt-4 flex justify-end gap-2">
                <button type="button" onClick={() => setStep('upload')} className="rounded border border-slate-300 px-4 py-2 text-slate-700 hover:bg-slate-50">
                  Indietro
                </button>
                <button
                  type="button"
                  onClick={handleImport}
                  disabled={validCount === 0 || loading}
                  className="rounded bg-indigo-600 px-4 py-2 text-white hover:bg-indigo-700 disabled:opacity-50"
                >
                  {loading ? 'Importazione...' : `Importa ${validCount} utenti`}
                </button>
              </div>
            </>
          )}

          {step === 'results' && result && (
            <>
              <p className="mt-2 text-sm text-slate-600">
                Creati: {result.created} — Saltati (già esistenti): {result.skipped} — Errori: {result.errors.length}
              </p>
              {result.errors.length > 0 && (
                <ul className="mt-2 max-h-32 overflow-y-auto rounded bg-red-50 p-2 text-sm text-red-700">
                  {result.errors.map((e, i) => (
                    <li key={i}>Riga {e.row} ({e.email}): {e.errors.join(', ')}</li>
                  ))}
                </ul>
              )}
              <div className="mt-6 flex justify-end">
                <button type="button" onClick={handleClose} className="rounded bg-indigo-600 px-4 py-2 text-white hover:bg-indigo-700">
                  Chiudi
                </button>
              </div>
            </>
          )}
        </Dialog.Panel>
      </div>
    </Dialog>
  )
}
