import { Link } from "react-router-dom";

import { ChangeList } from "../components/ChangeList";
import { Card, PageHeader } from "../components/Layout";
import { RunStatus } from "../components/RunStatus";
import { stagger, useCountUp } from "../components/Motion";
import { EmptyState, ErrorState, LoadingState } from "../components/States";
import { StatusBadge } from "../components/StatusBadge";
import { useApi } from "../hooks/useApi";
import { useUser } from "../hooks/useAuth";
import { he } from "../i18n/he";
import { api } from "../services/api";
import { formatRelative } from "../services/format";

const d = he.dashboard;

function CountUp({ value }: { value: number | undefined }) {
  const shown = useCountUp(value);
  return <>{shown == null ? he.common.none : shown.toLocaleString("he-IL")}</>;
}

function StatCard({ label, value, to, index = 0 }: { label: string; value: React.ReactNode; to?: string; index?: number }) {
  const body = (
    <div style={stagger(index, 60)}
         className={`h-full animate-enter rounded-lg border border-slate-200 bg-white p-4 shadow-sm transition-[border-color,box-shadow,translate] duration-200 ${
           to ? "hover:-translate-y-0.5 hover:border-slate-300 hover:shadow-md" : ""}`}>
      <p className="text-xs font-medium text-slate-500">{label}</p>
      <p className="mt-1 text-2xl font-semibold tabular-nums text-slate-900">{value}</p>
    </div>
  );
  return to ? <Link to={to} className="block rounded-lg">{body}</Link> : body;
}

export function DashboardPage() {
  const isAdmin = useUser().is_admin;  // run information is for admins only
  const stats = useApi(api.stats, "stats");
  const activity = useApi(() => api.activity(15), "activity");
  const s = stats.data;
  const run = s?.latest_run;

  return (
    <>
      <PageHeader title={d.title} subtitle={isAdmin && run ? d.lastRun(formatRelative(run.started_at)) : undefined} />
      {stats.error && <div className="mb-4"><ErrorState error={stats.error} onRetry={stats.reload} /></div>}

      <div className={`grid grid-cols-2 gap-3 md:grid-cols-3 ${isAdmin ? "lg:grid-cols-6" : "lg:grid-cols-4"}`}>
        <StatCard index={0} label={d.cards.activeJobs} value={<CountUp value={s?.active_jobs} />} to="/jobs?status=active" />
        <StatCard index={1} label={d.cards.newJobs} value={<CountUp value={s?.new_jobs} />} />
        <StatCard index={2} label={d.cards.updatedJobs} value={<CountUp value={s?.updated_jobs} />} />
        {isAdmin && <>
          <StatCard index={3} label={d.cards.lastRun} value={run ? <StatusBadge status={run.status} /> : he.common.none} />
          <StatCard index={4} label={d.cards.scrapersOk} value={run ? <span className="ltr">{run.sites_succeeded}/{run.sites_total}</span> : he.common.none} to="/sources" />
        </>}
      </div>

      <div className={`mt-6 grid gap-6 ${isAdmin ? "lg:grid-cols-3" : ""}`}>
        <div className={`min-w-0 ${isAdmin ? "lg:col-span-2" : ""}`}>
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
        {isAdmin && (
          <Card title={d.runHealth}>
            {stats.loading && !s ? <LoadingState /> : run ? (
              <RunStatus run={run} failedSources={s?.failed_sources} />
            ) : (
              <EmptyState title={d.noRuns} />
            )}
          </Card>
        )}
      </div>
    </>
  );
}
