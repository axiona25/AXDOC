import { Link } from 'react-router-dom'
import { FileExplorer } from '../components/documents/FileExplorer'

export function DocumentsPage() {
  return (
    <div className="flex h-[calc(100vh-8rem)] flex-col rounded-lg border border-slate-200 bg-white shadow dark:border-slate-700 dark:bg-slate-800">
      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-200 px-4 py-2 dark:border-slate-700">
        <h1 className="text-xl font-semibold text-slate-800 dark:text-slate-100">Documenti</h1>
        <Link
          to="/tools/p7m-verify"
          className="text-sm font-medium text-indigo-600 hover:text-indigo-800 hover:underline dark:text-indigo-400 dark:hover:text-indigo-300"
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
