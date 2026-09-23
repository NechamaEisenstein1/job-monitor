import { Card, PageHeader, td, th } from "../components/Layout";
import { EmptyState, ErrorState, LoadingState } from "../components/States";
import { Badge, StatusBadge } from "../components/StatusBadge";
import { useApi } from "../hooks/useApi";
import { he } from "../i18n/he";
import { api } from "../services/api";
import { formatDateTime } from "../services/format";

const s = he.sources;

export function SourcesPage() {
  const sources = useApi(api.sources, "sources");
  const c = s.columns;

  return (
    <>
      <PageHeader title={s.title} subtitle={s.subtitle} />
      <Card flush>
        {sources.error ? <div className="p-4"><ErrorState error={sources.error} onRetry={sources.reload} /></div>
          : !sources.data ? <LoadingState />
          : !sources.data.length ? <EmptyState title={s.empty} hint={s.emptyHint} />
          : (
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-slate-100">
                <thead className="bg-slate-50">
                  <tr>
                    {[c.source, c.lastStatus, c.lastRun, c.lastSuccess, c.fetched, c.active, c.lastError].map((h) => (
                      <th key={h} className={th}>{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {sources.data.map((src) => (
                    <tr key={src.name} className={src.enabled ? "" : "bg-slate-50/60 text-slate-400"}>
                      <td className={td}>
                        <div className="font-medium text-slate-900">{src.name}</div>
                        {src.note && <div className="mt-0.5 max-w-xs text-xs text-slate-500">{src.note}</div>}
                      </td>
                      <td className={td}>{src.enabled ? <StatusBadge status={src.last_status} /> : <Badge tone="slate">{s.disabled}</Badge>}</td>
                      <td className={`${td} whitespace-nowrap`}>{formatDateTime(src.last_run_at)}</td>
                      <td className={`${td} whitespace-nowrap`}>{formatDateTime(src.last_successful_at)}</td>
                      <td className={`${td} tabular-nums`}>{src.jobs_fetched ?? he.common.none}</td>
                      <td className={`${td} tabular-nums`}>{src.active_job_sources.toLocaleString("he-IL")}</td>
                      <td className={`${td} max-w-sm text-xs text-rose-700`}>
                        {src.last_error ? <span className="ltr block text-start">{src.last_error}</span> : <span className="text-slate-400">{he.common.none}</span>}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
      </Card>
    </>
  );
}
