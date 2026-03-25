import { Link, useLocation } from 'react-router-dom'
import { Home, ChevronRight } from 'lucide-react'
import { useBreadcrumbTitle } from './BreadcrumbContext'

const routeLabels: Record<string, string> = {
  dashboard: 'Dashboard',
  documents: 'Documenti',
  protocols: 'Protocolli',
  dossiers: 'Fascicoli',
  workflows: 'Workflow',
  users: 'Utenti',
  organizations: 'Organizzazioni',
  groups: 'Gruppi',
  settings: 'Impostazioni',
  profile: 'Profilo',
  search: 'Ricerca',
  audit: 'Audit Log',
  archive: 'Archivio',
  mail: 'Posta',
  metadata: 'Metadati',
  'registro-giornaliero': 'Registro Giornaliero',
  tools: 'Strumenti',
  'p7m-verify': 'Verifica P7M',
  admin: 'Amministrazione',
  license: 'Licenza',
  'document-templates': 'Template documenti',
}

function isUuidSegment(s: string): boolean {
  return /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i.test(s)
}

export function Breadcrumb() {
  const { pathname } = useLocation()
  const { entityTitle } = useBreadcrumbTitle()

  const parts = pathname.replace(/\/$/, '').split('/').filter(Boolean)

  type Crumb = { to: string; label: string; isLast: boolean; isHome?: boolean }
  const crumbs: Crumb[] = []

  if (parts.length === 0 || (parts.length === 1 && parts[0] === 'dashboard')) {
    crumbs.push({ to: '/dashboard', label: 'Dashboard', isLast: true, isHome: true })
  } else {
    crumbs.push({ to: '/dashboard', label: 'Home', isLast: false, isHome: true })
    let acc = ''
    parts.forEach((seg, i) => {
      acc += `/${seg}`
      const isLast = i === parts.length - 1
      let label = routeLabels[seg] ?? seg
      if (isUuidSegment(seg) && isLast && entityTitle) {
        label = entityTitle
      } else if (isUuidSegment(seg) && isLast) {
        label = `…${seg.slice(0, 8)}`
      }
      crumbs.push({ to: acc, label, isLast })
    })
  }

  return (
    <nav
      className="flex flex-wrap items-center gap-1 text-sm text-slate-500 dark:text-slate-400"
      aria-label="Percorso"
    >
      {crumbs.map((c, idx) => (
        <span key={`${c.to}-${idx}`} className="flex items-center gap-1">
          {idx > 0 && (
            <ChevronRight className="h-3.5 w-3.5 shrink-0 text-slate-400 dark:text-slate-500" aria-hidden />
          )}
          {c.isHome ? (
            <Link
              to={c.to}
              className={`inline-flex items-center gap-0.5 hover:text-indigo-600 dark:hover:text-indigo-400 ${
                c.isLast ? 'font-medium text-slate-900 dark:text-slate-100' : 'text-slate-600 dark:text-slate-300'
              }`}
            >
              <Home className="h-3.5 w-3.5" aria-hidden />
              {!c.isLast && <span className="sr-only sm:not-sr-only">{c.label}</span>}
              {c.isLast && <span>{c.label}</span>}
            </Link>
          ) : c.isLast ? (
            <span className="font-medium text-slate-900 dark:text-slate-100">{c.label}</span>
          ) : (
            <Link to={c.to} className="hover:text-indigo-600 dark:hover:text-indigo-400">
              {c.label}
            </Link>
          )}
        </span>
      ))}
    </nav>
  )
}
