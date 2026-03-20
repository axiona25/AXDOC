import { useState, useEffect, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { getDailyRegister } from '../services/protocolService'
import type { ProtocolItem } from '../services/protocolService'

function formatDateForInput(d: Date): string {
  const y = d.getFullYear()
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${y}-${m}-${day}`
}

export function DailyRegisterPage() {
  const navigate = useNavigate()
  const [date, setDate] = useState(() => formatDateForInput(new Date()))
  const [data, setData] = useState<{ date: string; protocols: ProtocolItem[] } | null>(null)
  const [loading, setLoading] = useState(false)

  const load = useCallback(() => {
    if (!date) return
    setLoading(true)
    getDailyRegister(date)
      .then(setData)
      .catch(() => setData({ date, protocols: [] }))
      .finally(() => setLoading(false))
  }, [date])

  useEffect(() => {
    load()
  }, [load])

  const handlePrint = () => {
    window.print()
  }

  const segnatura = (p: ProtocolItem) => p.segnatura || p.protocol_id || p.protocol_display || p.id

  return (
    <div className="flex flex-col rounded-lg bg-white shadow print:shadow-none">
      <div className="border-b border-slate-200 px-4 py-3 print:border-b">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div>
            <button
              type="button"
              onClick={() => navigate('/protocols')}
              className="text-sm text-indigo-600 hover:underline print:hidden"
            >
              ← Protocolli
            </button>
            <h1 className="mt-1 text-xl font-semibold text-slate-800">Registro giornaliero</h1>
            <p className="text-sm text-slate-500">Elenco protocolli per data (segnatura AGID)</p>
          </div>
          <div className="flex flex-wrap items-center gap-2 print:hidden">
            <label className="flex items-center gap-2 text-sm">
              <span className="text-slate-600">Data:</span>
              <input
                type="date"
                value={date}
                onChange={(e) => setDate(e.target.value)}
                className="rounded border border-slate-300 px-2 py-1.5 text-sm"
              />
            </label>
            <button
              type="button"
              onClick={load}
              disabled={loading}
              className="rounded bg-indigo-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-50"
            >
              {loading ? 'Caricamento...' : 'Aggiorna'}
            </button>
            <button
              type="button"
              onClick={handlePrint}
              className="rounded bg-slate-100 px-3 py-1.5 text-sm font-medium text-slate-700 hover:bg-slate-200"
            >
              Stampa
            </button>
          </div>
        </div>
      </div>

      <div className="min-h-[200px] overflow-auto p-4">
        {loading && !data && <p className="text-slate-500">Caricamento...</p>}
        {data && (
          <>
            <p className="mb-3 text-sm text-slate-600">
              Data: <strong>{data.date}</strong> — {data.protocols.length} protocollo/i
            </p>
            {data.protocols.length === 0 ? (
              <p className="text-slate-500">Nessun protocollo registrato in questa data.</p>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full border-collapse text-sm">
                  <thead>
                    <tr className="border-b border-slate-200 bg-slate-50">
                      <th className="px-3 py-2 text-left font-medium text-slate-700">Segnatura</th>
                      <th className="px-3 py-2 text-left font-medium text-slate-700">Data e ora</th>
                      <th className="px-3 py-2 text-left font-medium text-slate-700">Tipologia</th>
                      <th className="px-3 py-2 text-left font-medium text-slate-700">Mittente / Destinatario</th>
                      <th className="px-3 py-2 text-left font-medium text-slate-700">Oggetto</th>
                      <th className="px-3 py-2 text-left font-medium text-slate-700">U.O.</th>
                      <th className="px-3 py-2 text-left font-medium text-slate-700 print:hidden">Azione</th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.protocols.map((p) => (
                      <tr key={p.id} className="border-b border-slate-100 hover:bg-slate-50/50">
                        <td className="px-3 py-2 font-mono font-medium text-slate-800">{segnatura(p)}</td>
                        <td className="px-3 py-2 text-slate-600">
                          {p.registered_at ? new Date(p.registered_at).toLocaleString('it-IT') : '—'}
                        </td>
                        <td className="px-3 py-2">
                          <span className={p.direction === 'in' ? 'text-blue-600' : 'text-amber-700'}>
                            {p.direction === 'in' ? 'In entrata' : 'In uscita'}
                          </span>
                        </td>
                        <td className="px-3 py-2 text-slate-700">{p.sender_receiver || '—'}</td>
                        <td className="px-3 py-2 text-slate-700">{p.subject || '—'}</td>
                        <td className="px-3 py-2 text-slate-600">{p.organizational_unit_name || '—'}</td>
                        <td className="px-3 py-2 print:hidden">
                          <button
                            type="button"
                            onClick={() => navigate(`/protocols/${p.id}`)}
                            className="text-indigo-600 hover:underline"
                          >
                            Dettaglio
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  )
}
