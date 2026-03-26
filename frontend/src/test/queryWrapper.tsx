import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { useMemo, type ReactNode } from 'react'

export function createTestQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  })
}

export function TestQueryProvider({ children }: { children: ReactNode }) {
  const client = useMemo(() => createTestQueryClient(), [])
  return <QueryClientProvider client={client}>{children}</QueryClientProvider>
}
