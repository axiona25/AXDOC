export function PageLoader() {
  return (
    <div className="min-h-screen bg-slate-100 p-6 dark:bg-slate-900">
      <div className="animate-pulse no-transition">
        <div className="mb-6 h-12 rounded-lg bg-slate-200 dark:bg-slate-700" />
        <div className="mb-6 grid grid-cols-1 gap-4 md:grid-cols-3">
          <div className="h-24 rounded-lg bg-slate-200 dark:bg-slate-700" />
          <div className="h-24 rounded-lg bg-slate-200 dark:bg-slate-700" />
          <div className="h-24 rounded-lg bg-slate-200 dark:bg-slate-700" />
        </div>
        <div className="h-64 rounded-lg bg-slate-200 dark:bg-slate-700" />
      </div>
    </div>
  )
}
