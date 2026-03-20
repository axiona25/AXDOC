import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { getLicense, getSystemInfo } from '../services/licenseService'

export function LicensePage() {
  const { data: licenseData, isLoading: licenseLoading } = useQuery({
    queryKey: ['license'],
    queryFn: getLicense,
  })
  const { data: systemInfo, isLoading: infoLoading } = useQuery({
    queryKey: ['system-info'],
    queryFn: getSystemInfo,
  })

  const lic = licenseData?.license
  const stats = licenseData?.stats

  return (
    <div className="min-h-screen bg-slate-100 p-6">
      <header className="mb-6 flex items-center justify-between">
        <h1 className="text-2xl font-bold text-slate-800">Licenza e sistema</h1>
        <Link to="/dashboard" className="text-indigo-600 hover:underline">Dashboard</Link>
      </header>

      {licenseLoading ? (
        <p className="text-slate-600">Caricamento...</p>
      ) : (
        <div className="space-y-6">
          <div className="rounded-lg border border-slate-200 bg-white p-6 shadow">
            <h2 className="text-lg font-semibold text-slate-800">Licenza</h2>
            {lic ? (
              <>
                <p className="mt-2 text-slate-700">
                  <span className="font-medium">Organizzazione:</span> {lic.organization_name}
                </p>
                <p className="text-slate-700">
                  <span className="font-medium">Valida fino a:</span>{' '}
                  {lic.expires_at ? new Date(lic.expires_at).toLocaleDateString('it-IT') : 'Perpetua'}
                </p>
                {stats && (
                  <>
                    <p className="mt-2 text-slate-700">
                      Utenti: {stats.active_users}
                      {stats.storage_limit_gb != null && ` / ${lic.max_users ?? '—'}`}
                    </p>
                    <p className="text-slate-700">
                      Storage: {stats.storage_used_gb} GB
                      {stats.storage_limit_gb != null && ` / ${stats.storage_limit_gb} GB`}
                    </p>
                    {stats.expires_in_days != null && stats.expires_in_days <= 30 && !stats.is_expired && (
                      <p className="mt-2 rounded bg-amber-50 p-2 text-amber-800 text-sm">
                        La licenza scade tra {stats.expires_in_days} giorni. Contatta il supporto.
                      </p>
                    )}
                    {stats.is_expired && (
                      <p className="mt-2 rounded bg-red-50 p-2 text-red-800 text-sm">
                        Licenza scaduta.
                      </p>
                    )}
                  </>
                )}
                {lic.features_enabled && Object.keys(lic.features_enabled).length > 0 && (
                  <div className="mt-3 flex flex-wrap gap-2">
                    {Object.entries(lic.features_enabled).map(([feature, enabled]) => (
                      <span
                        key={feature}
                        className={`rounded px-2 py-0.5 text-xs ${enabled ? 'bg-green-100 text-green-800' : 'bg-slate-100 text-slate-600'}`}
                      >
                        {feature}: {enabled ? 'Sì' : 'No'}
                      </span>
                    ))}
                  </div>
                )}
              </>
            ) : (
              <p className="mt-2 text-slate-600">Nessuna licenza configurata. Esegui: <code className="rounded bg-slate-100 px-1">python manage.py setup_license --org-name "..."</code></p>
            )}
          </div>

          <div className="rounded-lg border border-slate-200 bg-white p-6 shadow">
            <h2 className="text-lg font-semibold text-slate-800">Stato sistema</h2>
            {infoLoading ? (
              <p className="mt-2 text-slate-600">Caricamento...</p>
            ) : systemInfo ? (
              <dl className="mt-2 grid grid-cols-2 gap-2 text-sm">
                <dt className="text-slate-500">Django</dt>
                <dd>{systemInfo.django_version}</dd>
                <dt className="text-slate-500">Python</dt>
                <dd>{systemInfo.python_version}</dd>
                <dt className="text-slate-500">Database</dt>
                <dd>{systemInfo.database_size_mb} MB</dd>
                <dt className="text-slate-500">Redis</dt>
                <dd>{systemInfo.redis_connected ? 'Connesso' : 'Non connesso'}</dd>
                <dt className="text-slate-500">LDAP</dt>
                <dd>{systemInfo.ldap_connected ? 'Connesso' : 'Non connesso'}</dd>
                <dt className="text-slate-500">Firma digitale</dt>
                <dd>{systemInfo.signature_provider}</dd>
                <dt className="text-slate-500">Conservazione</dt>
                <dd>{systemInfo.conservation_provider}</dd>
              </dl>
            ) : null}
          </div>
        </div>
      )}
    </div>
  )
}
