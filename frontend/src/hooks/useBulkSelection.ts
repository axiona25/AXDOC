import { useCallback, useState } from 'react'

export function useBulkSelection<T extends string>() {
  const [selectedIds, setSelectedIds] = useState<Set<T>>(new Set())

  const toggle = useCallback((id: T) => {
    setSelectedIds((prev) => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  }, [])

  const selectAll = useCallback((ids: T[]) => {
    setSelectedIds(new Set(ids))
  }, [])

  const deselectAll = useCallback(() => {
    setSelectedIds(new Set())
  }, [])

  const setSelection = useCallback((next: Set<T>) => {
    setSelectedIds(next)
  }, [])

  const isSelected = useCallback((id: T) => selectedIds.has(id), [selectedIds])

  const count = selectedIds.size
  const hasSelection = count > 0
  const ids = Array.from(selectedIds)

  return {
    selectedIds,
    toggle,
    selectAll,
    deselectAll,
    setSelection,
    isSelected,
    count,
    hasSelection,
    ids,
  }
}
