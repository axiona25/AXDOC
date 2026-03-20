import { useState } from 'react'
import type { OrganizationalUnit } from '../../services/organizationService'

interface OUTreeProps {
  units: OrganizationalUnit[]
  selectedId: string | null
  onSelect: (ou: OrganizationalUnit) => void
  onEdit?: (ou: OrganizationalUnit) => void
  onExport?: (ou: OrganizationalUnit) => void
}

export function OUTree({
  units,
  selectedId,
  onSelect,
  onEdit,
  onExport,
}: OUTreeProps) {
  return (
    <ul className="list-none pl-0">
      {units.map((ou) => (
        <OUTreeNode
          key={ou.id}
          ou={ou}
          selectedId={selectedId}
          onSelect={onSelect}
          onEdit={onEdit}
          onExport={onExport}
          level={0}
        />
      ))}
    </ul>
  )
}

function OUTreeNode({
  ou,
  selectedId,
  onSelect,
  onEdit,
  onExport,
  level,
}: {
  ou: OrganizationalUnit
  selectedId: string | null
  onSelect: (ou: OrganizationalUnit) => void
  onEdit?: (ou: OrganizationalUnit) => void
  onExport?: (ou: OrganizationalUnit) => void
  level: number
}) {
  const [expanded, setExpanded] = useState(true)
  const hasChildren = ou.children && ou.children.length > 0
  const isSelected = selectedId === ou.id

  return (
    <li className="py-0.5">
      <div
        className="flex items-center gap-2 rounded px-2 py-1.5 hover:bg-slate-100"
        style={{ paddingLeft: `${level * 12 + 8}px` }}
      >
        <button
          type="button"
          onClick={() => setExpanded(!expanded)}
          className="w-5 text-slate-500"
        >
          {hasChildren ? (expanded ? '▼' : '▶') : '·'}
        </button>
        <button
          type="button"
          onClick={() => onSelect(ou)}
          className={`flex-1 text-left text-sm ${isSelected ? 'font-semibold text-indigo-700' : 'text-slate-800'}`}
        >
          {ou.code} — {ou.name}
          {ou.members_count != null && (
            <span className="ml-2 text-xs text-slate-500">({ou.members_count})</span>
          )}
        </button>
        {onEdit && (
          <button
            type="button"
            onClick={(e) => { e.stopPropagation(); onEdit(ou) }}
            className="text-xs text-indigo-600 hover:underline"
          >
            Modifica
          </button>
        )}
        {onExport && (
          <button
            type="button"
            onClick={(e) => { e.stopPropagation(); onExport(ou) }}
            className="text-xs text-slate-600 hover:underline"
          >
            Esporta
          </button>
        )}
      </div>
      {hasChildren && expanded && (
        <ul className="list-none pl-0">
          {ou.children!.map((child) => (
            <OUTreeNode
              key={child.id}
              ou={child}
              selectedId={selectedId}
              onSelect={onSelect}
              onEdit={onEdit}
              onExport={onExport}
              level={level + 1}
            />
          ))}
        </ul>
      )}
    </li>
  )
}
