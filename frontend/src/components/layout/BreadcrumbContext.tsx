import { createContext, useCallback, useContext, useMemo, useState, type ReactNode } from 'react'

interface BreadcrumbContextType {
  entityTitle: string | null
  setEntityTitle: (title: string | null) => void
}

const BreadcrumbContext = createContext<BreadcrumbContextType | null>(null)

export function BreadcrumbProvider({ children }: { children: ReactNode }) {
  const [entityTitle, setEntityTitleState] = useState<string | null>(null)

  const setEntityTitle = useCallback((title: string | null) => {
    setEntityTitleState(title)
  }, [])

  const value = useMemo(
    () => ({ entityTitle, setEntityTitle }),
    [entityTitle, setEntityTitle],
  )

  return <BreadcrumbContext.Provider value={value}>{children}</BreadcrumbContext.Provider>
}

export function useBreadcrumbTitle() {
  const ctx = useContext(BreadcrumbContext)
  if (!ctx) {
    return { entityTitle: null as string | null, setEntityTitle: (_: string | null) => {} }
  }
  return ctx
}
