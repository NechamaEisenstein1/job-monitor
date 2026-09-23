import { Link, useNavigate, useParams } from "react-router-dom";

import { BackLink, Card, PageHeader, td, th } from "../components/Layout";
import { ScraperStatus } from "../components/ScraperStatus";
import { EmptyState, ErrorState, LoadingState } from "../components/States";
import { StatusBadge } from "../components/StatusBadge";
import { useApi } from "../hooks/useApi";
import { he } from "../i18n/he";
import { api } from "../services/api";
import { formatDate, formatDateTime, formatDuration, formatPercent } from "../services/format";

const r = he.runs;

export function RunsPage() {
  const runs = useApi(api.runs, "runs");
  const navigate = useNavigate();
  const c = r.columns;

  return (
    <>
      <PageHeader title={r.title} subtitle={r.subtitle} />
      <Card flush>
        {runs.error ? <div className="p-4"><ErrorState error={runs.error} onRetry={runs.reload} /></div>
          : !runs.data ? <LoadingState rows={6} />
          : !runs.data.length ? <EmptyState title={r.empty} hint="python -m backend.cli run" />
          : (
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-slate-100">
                <thead className="bg-slate-50">
                  <tr>
                    {[c.date, c.started, c.finished, c.duration, c.status, c.sites, c.jobsFound, c.eligible].map((h) => (
                      <th key={h} className={th}>{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {runs.data.map((run) => (
                    <tr key={run.id} onClick={() => navigate(`/runs/${run.id}`)} className="cursor-pointer hover:bg-slate-50">
                      <td className={td}>
                        <Link to={`/runs/${run.id}`} className="font-medium text-slate-900 hover:underline">{formatDate(run.scheduled_date)}</Link>
                      </td>
                      <td className={`${td} whitespace-nowrap`}>{formatDateTime(run.started_at)}</td>
                      <td className={`${td} whitespace-nowrap`}>{formatDateTime(run.finished_at)}</td>
                      <td className={td}>{formatDuration(run.duration_seconds)}</td>
                      <td className={td}><StatusBadge status={run.status} /></td>
                      <td className={`${td} tabular-nums`}><span className="ltr">{run.sites_succeeded}/{run.sites_total}</span></td>
                      <td className={`${td} tabular-nums`}>{run.raw_jobs_found.toLocaleString("he-IL")}</td>
                      <td className={`${td} tabular-nums`}>{run.eligible_jobs.toLocaleString("he-IL")}</td>
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

export function RunDetailsPage() {
  const id = useParams().id ?? "";
  const run = useApi(() => api.run(id), `run-${id}`);

  if (run.error) return <ErrorState error={run.error} onRetry={run.reload} />;
  if (!run.data) return <LoadingState rows={8} />;
  const d = run.data;
  const facts: [string, React.ReactNode][] = [
    [r.overallStatus, <StatusBadge status={d.status} />],
    [r.successRatio, <span className="ltr">{formatPercent(d.success_ratio)} ({d.sites_succeeded}/{d.sites_total})</span>],
    [r.duration, formatDuration(d.duration_seconds)],
    [r.foundValid, <span className="ltr">{d.raw_jobs_found} / {d.normalized_jobs}</span>],
    [r.touched, d.canonical_jobs_touched],
    [r.eligible, d.eligible_jobs],
  ];

  return (
    <>
      <BackLink to="/runs" label={r.back} />
      <PageHeader title={r.runTitle(formatDate(d.scheduled_date))} subtitle={<span className="ltr font-mono text-xs">{d.id}</span>} />
      <div className="space-y-6">
        <Card>
          <dl className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-6">
            {facts.map(([label, value]) => (
              <div key={label}>
                <dt className="text-xs text-slate-500">{label}</dt>
                <dd className="mt-0.5 text-sm font-medium tabular-nums text-slate-800">{value}</dd>
              </div>
            ))}
          </dl>
        </Card>
        <Card title={r.scrapers} flush><ScraperStatus scrapers={d.scrapers} /></Card>
      </div>
    </>
  );
}
