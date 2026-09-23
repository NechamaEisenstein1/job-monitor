import { Link } from "react-router-dom";

import { ChangeList } from "../components/ChangeList";
import { Card, PageHeader } from "../components/Layout";
import { RunStatus } from "../components/RunStatus";
import { EmptyState, ErrorState, LoadingState } from "../components/States";
import { StatusBadge } from "../components/StatusBadge";
import { useApi } from "../hooks/useApi";
import { he } from "../i18n/he";
import { api } from "../services/api";
import { formatRelative } from "../services/format";

const d = he.dashboard;

function StatCard({ label, value, to }: { label: string; value: React.ReactNode; to?: string }) {
  const body = (
    <div className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm transition-colors hover:border-slate-300">
      <p className="text-xs font-medium text-slate-500">{label}</p>
      <p className="mt-1 text-2xl font-semibold tabular-nums text-slate-900">{value}</p>
    </div>
  );
  return to ? <Link to={to}>{body}</Link> : body;
}

export function DashboardPage() {
  const stats = useApi(api.stats, "stats");
  const activity = useApi(() => api.activity(15), "activity");
  const s = stats.data;
  const run = s?.latest_run;
  const num = (n: number | undefined) => (n == null ? he.common.none : n.toLocaleString("he-IL"));

  return (
    <>
      <PageHeader title={d.title} subtitle={run ? d.lastRun(formatRelative(run.started_at)) : undefined} />
      {stats.error && <div className="mb-4"><ErrorState error={stats.error} onRetry={stats.reload} /></div>}

      <div className="grid grid-cols-2 gap-3 md:grid-cols-3 lg:grid-cols-6">
        <StatCard label={d.cards.activeJobs} value={num(s?.active_jobs)} to="/jobs?status=active" />
        <StatCard label={d.cards.newJobs} value={num(s?.new_jobs)} />
        <StatCard label={d.cards.updatedJobs} value={num(s?.updated_jobs)} />
        <StatCard label={d.cards.eligible} value={num(s?.eligible_jobs)} to="/jobs?eligible=true&status=active" />
        <StatCard label={d.cards.lastRun} value={run ? <StatusBadge status={run.status} /> : he.common.none} />
        <StatCard label={d.cards.scrapersOk} value={run ? <span className="ltr">{run.sites_succeeded}/{run.sites_total}</span> : he.common.none} to="/sources" />
      </div>

      <div className="mt-6 grid gap-6 lg:grid-cols-3">
        <div className="min-w-0 lg:col-span-2">
          <Card title={d.recentActivity} flush actions={<Link to="/jobs?sort=updated" className="text-sm text-sky-700 hover:underline">{d.allJobs}</Link>}>
            {activity.error ? (
              <div className="p-4"><ErrorState error={activity.error} onRetry={activity.reload} /></div>
            ) : activity.loading && !activity.data ? (
              <LoadingState rows={6} />
            ) : activity.data?.length ? (
              <ChangeList changes={activity.data} />
            ) : (
              <EmptyState title={d.noActivity} hint={d.noActivityHint} />
            )}
          </Card>
        </div>
        <Card title={d.runHealth}>
          {stats.loading && !s ? <LoadingState /> : run ? (
            <RunStatus run={run} failedSources={s?.failed_sources} />
          ) : (
            <EmptyState title={d.noRuns} />
          )}
        </Card>
      </div>
    </>
  );
}
