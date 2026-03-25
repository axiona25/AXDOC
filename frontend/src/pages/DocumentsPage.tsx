import { Link } from 'react-router-dom'
import { FileExplorer } from '../components/documents/FileExplorer'

export function DocumentsPage() {
  return (
    <div className="flex h-[calc(100vh-8rem)] flex-col rounded-lg bg-white shadow">
      <div className="border-b border-slate-200 px-4 py-2 flex flex-wrap items-center justify-between gap-2">
        <h1 className="text-xl font-semibold text-slate-800">Documenti</h1>
        <Link
          to="/tools/p7m-verify"
          className="text-sm font-medium text-indigo-600 hover:text-indigo-800 hover:underline"
        >
          Verifica P7M
        </Link>
      </div>
      <div className="min-h-0 flex-1">
        <FileExplorer />
      </div>
    </div>
  )
}
