import { FileExplorer } from '../components/documents/FileExplorer'

export function DocumentsPage() {
  return (
    <div className="flex h-[calc(100vh-8rem)] flex-col rounded-lg bg-white shadow">
      <div className="border-b border-slate-200 px-4 py-2">
        <h1 className="text-xl font-semibold text-slate-800">Documenti</h1>
      </div>
      <div className="min-h-0 flex-1">
        <FileExplorer />
      </div>
    </div>
  )
}
