import { Link } from "react-router-dom";

import type { ScrapeRun } from "../types/api";
import { he } from "../i18n/he";
import { formatDateTime, formatDuration, formatPercent } from "../services/format";
import { StatusBadge } from "./StatusBadge";

/** Compact health summary of one ScrapeRun. */
export function RunStatus({ run, failedSources }: { run: ScrapeRun; failedSources?: string[] }) {
  const facts: [string, React.ReactNode][] = [
    [he.runs.overallStatus, <StatusBadge status={run.status} />],
    [he.runs.started, formatDateTime(run.started_at)],
    [he.runs.duration, formatDuration(run.duration_seconds)],
    [he.runs.successRatio, <span className="tabular-nums">{formatPercent(run.success_ratio)} ({run.sites_succeeded}/{run.sites_total})</span>],
  ];
  return (
    <div className="space-y-3">
      <dl className="grid grid-cols-2 gap-x-4 gap-y-3 text-sm">
        {facts.map(([label, value]) => (
          <div key={label}>
            <dt className="text-xs text-slate-500">{label}</dt>
            <dd className="mt-0.5 font-medium text-slate-800">{value}</dd>
          </div>
        ))}
      </dl>
      {failedSources && failedSources.length > 0 && (
        <p className="rounded-md bg-rose-50 px-3 py-2 text-sm text-rose-800">
          {he.runs.failedSources(failedSources.join(", "))}
        </p>
      )}
      <Link to={`/runs/${run.id}`} className="inline-block text-sm font-medium text-sky-700 hover:underline">
        {he.runs.viewDetails}
      </Link>
    </div>
  );
}
