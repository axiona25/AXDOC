import { useState } from 'react'
import { Link } from 'react-router-dom'
import { P7MViewer } from '../components/viewer/P7MViewer'

export function P7MVerifyPage() {
  const [file, setFile] = useState<File | null>(null)
  const [pickHint, setPickHint] = useState('')

  return (
    <div className="min-h-screen bg-slate-100 p-4 md:p-6">
      <header className="mb-4 flex flex-wrap items-center justify-between gap-2 rounded-lg bg-white p-3 shadow md:p-4">
        <div>
          <h1 className="text-lg font-bold text-slate-800 md:text-xl">Verifica firma P7M (CAdES)</h1>
          <p className="text-sm text-slate-600 mt-1">
            Carica un file <code className="rounded bg-slate-100 px-1">.p7m</code> per verificarne la firma o estrarre il documento originale.
          </p>
        </div>
        <Link to="/dashboard" className="text-sm text-indigo-600 hover:underline">
          ← Dashboard
        </Link>
      </header>

      <div className="rounded-lg bg-white shadow overflow-hidden flex flex-col min-h-[calc(100vh-12rem)]">
        <div className="border-b border-slate-200 px-4 py-3 flex flex-wrap items-center gap-3">
          <label className="inline-flex cursor-pointer items-center gap-2 rounded border border-slate-300 bg-slate-50 px-3 py-2 text-sm font-medium text-slate-700 hover:bg-slate-100">
            <span>Scegli file .p7m</span>
            <input
              type="file"
              accept=".p7m,application/pkcs7-mime,application/x-pkcs7-mime"
              className="sr-only"
              onChange={(e) => {
                setPickHint('')
                const f = e.target.files?.[0] ?? null
                if (!f) {
                  setFile(null)
                  return
                }
                if (!f.name.toLowerCase().endsWith('.p7m')) {
                  setPickHint('Seleziona un file con estensione .p7m.')
                  setFile(null)
                  e.target.value = ''
                  return
                }
                setFile(f)
              }}
            />
          </label>
          {file && (
            <button
              type="button"
              onClick={() => setFile(null)}
              className="text-sm text-slate-600 hover:text-slate-900 underline"
            >
              Rimuovi file
            </button>
          )}
          {pickHint && <span className="text-sm text-amber-700">{pickHint}</span>}
        </div>

        <div className="flex-1 min-h-0">
          {file ? (
            <P7MViewer file={file} fileName={file.name} />
          ) : (
            <div className="flex flex-col items-center justify-center py-20 text-slate-500 px-4 text-center">
              <span className="text-5xl mb-4">📤</span>
              <p className="text-base font-medium text-slate-700">Nessun file selezionato</p>
              <p className="text-sm mt-2 max-w-md">
                Usa il pulsante sopra per selezionare un file firmato in formato P7M. I file vengono inviati al server solo quando avvii la verifica o
                l&apos;estrazione.
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
