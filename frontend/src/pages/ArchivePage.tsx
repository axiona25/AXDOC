import { useState, useEffect, useCallback } from 'react'
import {
  getArchiveDocuments,
  getPackages,
  getRetentionRules,
  moveToDeposit,
  downloadPackage,
} from '../services/archiveService'
import type { DocumentArchiveItem, InformationPackageItem, RetentionRuleItem } from '../services/archiveService'
import { PackageWizard } from '../components/archive/PackageWizard'

type TabId = 'current' | 'deposit' | 'historical' | 'packages' | 'retention'

const STAGE_BADGE: Record<string, { label: string; className: string }> = {
  not_sent: { label: 'Non inviato', className: 'bg-slate-100 text-slate-700' },
  pending: { label: 'In attesa', className: 'bg-amber-100 text-amber-800' },
  accepted: { label: 'Accettato', className: 'bg-green-100 text-green-800' },
  rejected: { label: 'Rifiutato', className: 'bg-red-100 text-red-800' },
}

export function ArchivePage() {
  const [tab, setTab] = useState<TabId>('current')
  const [currentDocs, setCurrentDocs] = useState<DocumentArchiveItem[]>([])
  const [depositDocs, setDepositDocs] = useState<DocumentArchiveItem[]>([])
  const [historicalDocs, setHistoricalDocs] = useState<DocumentArchiveItem[]>([])
  const [packages, setPackages] = useState<InformationPackageItem[]>([])
  const [rules, setRules] = useState<RetentionRuleItem[]>([])
  const [loading, setLoading] = useState(false)
  const [wizardOpen, setWizardOpen] = useState(false)

  const load = useCallback(() => {
    setLoading(true)
    Promise.all([
      getArchiveDocuments('current').then(setCurrentDocs).catch(() => setCurrentDocs([])),
      getArchiveDocuments('deposit').then(setDepositDocs).catch(() => setDepositDocs([])),
      getArchiveDocuments('historical').then(setHistoricalDocs).catch(() => setHistoricalDocs([])),
      getPackages().then(setPackages).catch(() => setPackages([])),
      getRetentionRules().then(setRules).catch(() => setRules([])),
    ]).finally(() => setLoading(false))
  }, [])

  useEffect(() => {
    load()
  }, [load])

  const handleMoveToDeposit = async (id: number) => {
    try {
      await moveToDeposit(id)
      load()
    } catch (e) {
      alert((e as Error)?.message)
    }
  }

  const handleDownloadPkg = async (pkg: InformationPackageItem) => {
    try {
      const blob = await downloadPackage(pkg.id)
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `${pkg.package_id}.zip`
      a.click()
      URL.revokeObjectURL(url)
    } catch {
      alert('Download non disponibile')
    }
  }

  const tabs: { id: TabId; label: string }[] = [
    { id: 'current', label: 'Archivio Corrente' },
    { id: 'deposit', label: 'Archivio di Deposito' },
    { id: 'historical', label: 'Archivio Storico' },
    { id: 'packages', label: 'Pacchetti Informativi' },
    { id: 'retention', label: 'Massimario di scarto' },
  ]

  return (
    <div className="flex flex-col rounded-lg bg-white shadow">
      <div className="border-b border-slate-200 px-4 py-3">
        <div className="flex items-center justify-between">
          <h1 className="text-xl font-semibold text-slate-800">Archivio Documentale</h1>
          <div className="flex gap-2">
            <button
              type="button"
              onClick={() => setWizardOpen(true)}
              className="rounded bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700"
            >
              Crea PdV
            </button>
            <span className="rounded bg-slate-100 px-3 py-1.5 text-sm text-slate-600">Massimario</span>
            <span className="rounded bg-slate-100 px-3 py-1.5 text-sm text-slate-600">Report</span>
          </div>
        </div>
      </div>
      <div className="flex gap-2 border-b border-slate-200 px-4">
        {tabs.map((t) => (
          <button
            key={t.id}
            type="button"
            onClick={() => setTab(t.id)}
            className={`border-b-2 px-3 py-2 text-sm font-medium ${tab === t.id ? 'border-indigo-600 text-indigo-600' : 'border-transparent text-slate-600'}`}
          >
            {t.label}
          </button>
        ))}
      </div>
      <div className="min-h-[300px] p-4">
        {loading && <p className="text-slate-500">Caricamento...</p>}

        {tab === 'current' && !loading && (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-slate-200 bg-slate-50">
                  <th className="px-3 py-2 text-left font-medium text-slate-700">Documento</th>
                  <th className="px-3 py-2 text-left font-medium text-slate-700">Data creazione</th>
                  <th className="px-3 py-2 text-left font-medium text-slate-700">Classificazione</th>
                  <th className="px-3 py-2 text-left font-medium text-slate-700">Anni conservazione</th>
                  <th className="px-3 py-2 text-right font-medium text-slate-700">Azioni</th>
                </tr>
              </thead>
              <tbody>
                {currentDocs.map((r) => (
                  <tr key={r.id} className="border-b border-slate-100">
                    <td className="px-3 py-2">{r.document_title || r.document}</td>
                    <td className="px-3 py-2">{r.created_at ? new Date(r.created_at).toLocaleDateString() : '—'}</td>
                    <td className="px-3 py-2">{r.classification_code || '—'} {r.classification_label ? ` ${r.classification_label}` : ''}</td>
                    <td className="px-3 py-2">{r.retention_years}</td>
                    <td className="px-3 py-2 text-right">
                      <button type="button" onClick={() => handleMoveToDeposit(r.id)} className="text-indigo-600 hover:underline mr-2">Sposta in deposito</button>
                      <span className="text-slate-400">Aggiungi a PdV</span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            {currentDocs.length === 0 && <p className="py-4 text-slate-500">Nessun documento in Archivio Corrente.</p>}
          </div>
        )}

        {tab === 'deposit' && !loading && (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-slate-200 bg-slate-50">
                  <th className="px-3 py-2 text-left font-medium text-slate-700">Documento</th>
                  <th className="px-3 py-2 text-left font-medium text-slate-700">Data archiviazione</th>
                  <th className="px-3 py-2 text-left font-medium text-slate-700">Scadenza conservazione</th>
                  <th className="px-3 py-2 text-right font-medium text-slate-700">Azioni</th>
                </tr>
              </thead>
              <tbody>
                {depositDocs.map((r) => (
                  <tr key={r.id} className="border-b border-slate-100">
                    <td className="px-3 py-2">{r.document_title || r.document}</td>
                    <td className="px-3 py-2">{r.archive_date ? new Date(r.archive_date).toLocaleDateString() : '—'}</td>
                    <td className="px-3 py-2">—</td>
                    <td className="px-3 py-2 text-right">
                      <button type="button" className="text-indigo-600 hover:underline mr-2">Sposta in storico</button>
                      <button type="button" className="text-amber-600 hover:underline mr-2">Richiedi scarto</button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            {depositDocs.length === 0 && <p className="py-4 text-slate-500">Nessun documento in Archivio di Deposito.</p>}
          </div>
        )}

        {tab === 'historical' && !loading && (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-slate-200 bg-slate-50">
                  <th className="px-3 py-2 text-left font-medium text-slate-700">Documento</th>
                  <th className="px-3 py-2 text-left font-medium text-slate-700">Data passaggio</th>
                  <th className="px-3 py-2 text-left font-medium text-slate-700">Stato conservazione</th>
                  <th className="px-3 py-2 text-right font-medium text-slate-700">Azioni</th>
                </tr>
              </thead>
              <tbody>
                {historicalDocs.map((r) => (
                  <tr key={r.id} className="border-b border-slate-100">
                    <td className="px-3 py-2">{r.document_title || r.document}</td>
                    <td className="px-3 py-2">{r.historical_date ? new Date(r.historical_date).toLocaleDateString() : '—'}</td>
                    <td className="px-3 py-2">
                      {(() => {
                        const b = STAGE_BADGE[r.conservation_status] || STAGE_BADGE.not_sent
                        return <span className={`rounded px-2 py-0.5 text-xs font-medium ${b.className}`}>{b.label}</span>
                      })()}
                    </td>
                    <td className="px-3 py-2 text-right">
                      <button type="button" className="text-indigo-600 hover:underline mr-2">Visualizza</button>
                      <span className="text-slate-400">Richiedi esibizione (PdD)</span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            {historicalDocs.length === 0 && <p className="py-4 text-slate-500">Nessun documento in Archivio Storico.</p>}
          </div>
        )}

        {tab === 'packages' && !loading && (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-slate-200 bg-slate-50">
                  <th className="px-3 py-2 text-left font-medium text-slate-700">Tipo</th>
                  <th className="px-3 py-2 text-left font-medium text-slate-700">Data</th>
                  <th className="px-3 py-2 text-left font-medium text-slate-700">Documenti / Prot. / Fasc.</th>
                  <th className="px-3 py-2 text-left font-medium text-slate-700">Stato</th>
                  <th className="px-3 py-2 text-left font-medium text-slate-700">Checksum</th>
                  <th className="px-3 py-2 text-right font-medium text-slate-700">Azioni</th>
                </tr>
              </thead>
              <tbody>
                {packages.map((p) => (
                  <tr key={p.id} className="border-b border-slate-100">
                    <td className="px-3 py-2">{p.package_type}</td>
                    <td className="px-3 py-2">{new Date(p.created_at).toLocaleDateString()}</td>
                    <td className="px-3 py-2">{p.document_count} / {p.protocol_count} / {p.dossier_count}</td>
                    <td className="px-3 py-2">{p.status}</td>
                    <td className="px-3 py-2 font-mono text-xs">{p.checksum ? `${p.checksum.slice(0, 12)}…` : '—'}</td>
                    <td className="px-3 py-2 text-right">
                      <button type="button" onClick={() => handleDownloadPkg(p)} className="text-indigo-600 hover:underline mr-2">Scarica</button>
                      <button type="button" className="text-slate-600 hover:underline mr-2">Invia al conservatore</button>
                      <button type="button" className="text-slate-600 hover:underline">Genera PdD</button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            {packages.length === 0 && <p className="py-4 text-slate-500">Nessun pacchetto.</p>}
          </div>
        )}

        {tab === 'retention' && !loading && (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-slate-200 bg-slate-50">
                  <th className="px-3 py-2 text-left font-medium text-slate-700">Codice</th>
                  <th className="px-3 py-2 text-left font-medium text-slate-700">Descrizione</th>
                  <th className="px-3 py-2 text-left font-medium text-slate-700">Anni</th>
                  <th className="px-3 py-2 text-left font-medium text-slate-700">Azione</th>
                </tr>
              </thead>
              <tbody>
                {rules.map((r) => (
                  <tr key={r.id} className="border-b border-slate-100">
                    <td className="px-3 py-2 font-mono">{r.classification_code}</td>
                    <td className="px-3 py-2">{r.classification_label}</td>
                    <td className="px-3 py-2">{r.retention_years}</td>
                    <td className="px-3 py-2">{r.action_after_retention}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            {rules.length === 0 && <p className="py-4 text-slate-500">Nessuna regola. Esegui: python manage.py init_titolario</p>}
          </div>
        )}
      </div>

      <PackageWizard
        open={wizardOpen}
        onClose={() => setWizardOpen(false)}
        onSuccess={() => { load(); setWizardOpen(false); }}
      />
    </div>
  )
}
