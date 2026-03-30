import type { ReactNode } from 'react'
import { BreadcrumbProvider } from './BreadcrumbContext'
import { Breadcrumb } from './Breadcrumb'
import { TenantSelector } from './TenantSelector'
import { PrivacyBanner } from '../auth/PrivacyBanner'

export function AuthenticatedLayout({ children }: { children: ReactNode }) {
  return (
    <BreadcrumbProvider>
      <div className="min-h-screen bg-slate-100 dark:bg-slate-900">
        <header role="banner" className="flex items-center justify-between gap-2 border-b border-slate-200 bg-white px-4 py-2 shadow-sm dark:border-slate-700 dark:bg-slate-800">
          <Breadcrumb />
          <div className="flex items-center gap-2">
            <TenantSelector />
          </div>
        </header>
        <PrivacyBanner />
        <main id="main-content" role="main" tabIndex={-1} className="outline-none">
          {children}
        </main>
      </div>
    </BreadcrumbProvider>
  )
}
