import { he } from "../i18n/he";

export function EmptyState({ title, hint }: { title: string; hint?: string }) {
  return (
    <div className="px-6 py-12 text-center">
      <p className="text-sm font-medium text-slate-700">{title}</p>
      {hint && <p className="mt-1 text-sm text-slate-500">{hint}</p>}
    </div>
  );
}

export function ErrorState({ error, onRetry }: { error: Error; onRetry?: () => void }) {
  return (
    <div role="alert" className="flex items-center justify-between gap-4 rounded-lg border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-800">
      <span>{he.common.loadError}: {error.message}</span>
      {onRetry && (
        <button onClick={onRetry} className="rounded-md bg-white px-3 py-1 font-medium ring-1 ring-rose-300 hover:bg-rose-100">
          {he.common.retry}
        </button>
      )}
    </div>
  );
}

export function LoadingState({ rows = 4 }: { rows?: number }) {
  return (
    <div className="space-y-2 p-4" aria-busy="true" aria-label={he.common.loading}>
      {Array.from({ length: rows }, (_, i) => (
        <div key={i} className="h-5 animate-pulse rounded bg-slate-100" />
      ))}
    </div>
  );
}
