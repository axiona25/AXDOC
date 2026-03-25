import { useCallback, useEffect, useState } from 'react'
import { useAuthStore } from '../../store/authStore'
import { getTenants, getTenantCurrent, type TenantInfo } from '../../services/tenantService'

const STORAGE_KEY = 'axdoc_tenant_context_id'

export function TenantSelector() {
  const user = useAuthStore((s) => s.user)
  const [current, setCurrent] = useState<TenantInfo | null>(null)
  const [tenants, setTenants] = useState<TenantInfo[]>([])
  const [open, setOpen] = useState(false)

  const loadCurrent = useCallback(() => {
    getTenantCurrent()
      .then(setCurrent)
      .catch(() => setCurrent(null))
  }, [])

  useEffect(() => {
    if (!user) {
      setCurrent(null)
      return
    }
    loadCurrent()
  }, [user, loadCurrent])

  useEffect(() => {
    if (!user?.is_superuser) return
    getTenants()
      .then((list) => {
        const arr = Array.isArray(list) ? list : (list as unknown as { results?: TenantInfo[] }).results ?? []
        setTenants(arr)
      })
      .catch(() => setTenants([]))
  }, [user?.is_superuser])

  const onSelect = (id: string) => {
    if (!id) {
      localStorage.removeItem(STORAGE_KEY)
    } else {
      localStorage.setItem(STORAGE_KEY, id)
    }
    setOpen(false)
    window.location.reload()
  }

  if (!user) return null

  return (
    <div className="relative flex items-center gap-2 text-sm">
      {current && (
        <span className="hidden max-w-[10rem] truncate rounded-md bg-slate-100 px-2 py-0.5 text-slate-700 dark:bg-slate-700 dark:text-slate-200 sm:inline">
          {current.name}
        </span>
      )}
      {user.is_superuser && tenants.length > 1 && (
        <>
          <button
            type="button"
            className="rounded border border-slate-300 px-2 py-0.5 text-xs dark:border-slate-600"
            onClick={() => setOpen((o) => !o)}
          >
            Tenant
          </button>
          {open && (
            <ul className="absolute right-0 top-full z-50 mt-1 max-h-60 min-w-[12rem] overflow-auto rounded border border-slate-200 bg-white py-1 shadow-lg dark:border-slate-600 dark:bg-slate-800">
              <li>
                <button
                  type="button"
                  className="block w-full px-3 py-1.5 text-left text-xs hover:bg-slate-100 dark:hover:bg-slate-700"
                  onClick={() => onSelect('')}
                >
                  Default (JWT)
                </button>
              </li>
              {tenants.map((t) => (
                <li key={t.id}>
                  <button
                    type="button"
                    className="block w-full px-3 py-1.5 text-left text-xs hover:bg-slate-100 dark:hover:bg-slate-700"
                    onClick={() => onSelect(t.id)}
                  >
                    {t.name}
                  </button>
                </li>
              ))}
            </ul>
          )}
        </>
      )}
    </div>
  )
}
