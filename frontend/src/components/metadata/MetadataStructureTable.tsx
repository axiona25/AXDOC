import type { MetadataStructure } from '../../types/metadata'

interface MetadataStructureTableProps {
  structures: MetadataStructure[]
  onEdit: (s: MetadataStructure) => void
  onPreview: (s: MetadataStructure) => void
  onDelete: (s: MetadataStructure) => void
}

export function MetadataStructureTable({
  structures,
  onEdit,
  onPreview,
  onDelete,
}: MetadataStructureTableProps) {
  return (
    <div className="overflow-auto rounded border border-slate-200">
      <table className="w-full min-w-[500px] border-collapse text-sm">
        <thead>
          <tr className="border-b border-slate-200 bg-slate-50">
            <th className="px-3 py-2 text-left font-medium text-slate-700">Nome</th>
            <th className="px-3 py-2 text-left font-medium text-slate-700">Campi</th>
            <th className="px-3 py-2 text-left font-medium text-slate-700">Documenti</th>
            <th className="px-3 py-2 text-left font-medium text-slate-700">Stato</th>
            <th className="px-3 py-2 text-right font-medium text-slate-700">Azioni</th>
          </tr>
        </thead>
        <tbody>
          {structures.map((s) => (
            <tr key={s.id} className="border-b border-slate-100 hover:bg-slate-50">
              <td className="px-3 py-2 font-medium text-slate-800">{s.name}</td>
              <td className="px-3 py-2 text-slate-600">{s.field_count ?? (s.fields?.length ?? 0)}</td>
              <td className="px-3 py-2 text-slate-600">{s.document_count ?? 0}</td>
              <td className="px-3 py-2">
                <span
                  className={`inline-block rounded px-2 py-0.5 text-xs font-medium ${s.is_active ? 'bg-green-100 text-green-800' : 'bg-slate-200 text-slate-600'}`}
                >
                  {s.is_active ? 'Attiva' : 'Inattiva'}
                </span>
              </td>
              <td className="px-3 py-2 text-right">
                <button
                  type="button"
                  onClick={() => onPreview(s)}
                  className="mr-2 rounded px-2 py-1 text-indigo-600 hover:bg-indigo-50"
                >
                  Anteprima
                </button>
                <button
                  type="button"
                  onClick={() => onEdit(s)}
                  className="mr-2 rounded px-2 py-1 text-slate-600 hover:bg-slate-100"
                >
                  Modifica
                </button>
                <button
                  type="button"
                  onClick={() => onDelete(s)}
                  className="rounded px-2 py-1 text-red-600 hover:bg-red-50"
                >
                  Elimina
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      {structures.length === 0 && (
        <div className="py-8 text-center text-slate-500">Nessuna struttura metadati.</div>
      )}
    </div>
  )
}
