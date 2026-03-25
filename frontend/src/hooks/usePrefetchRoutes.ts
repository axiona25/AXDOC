import { useEffect } from 'react'

/**
 * Precarica i chunk delle route più usate dopo il login (non blocca il primo paint).
 */
export function usePrefetchRoutes() {
  useEffect(() => {
    const timer = window.setTimeout(() => {
      void import('../pages/DocumentsPage')
      void import('../pages/ProtocolsPage')
      void import('../pages/DossiersPage')
    }, 2000)
    return () => window.clearTimeout(timer)
  }, [])
}
