import type { JobSource } from "../types/api";
import { he } from "../i18n/he";
import { formatDateTime } from "../services/format";
import { StatusBadge } from "./StatusBadge";

export function SourceList({ sources }: { sources: JobSource[] }) {
  return (
    <ul className="divide-y divide-slate-100">
      {sources.map((s) => (
        <li key={s.id} className="flex flex-wrap items-start justify-between gap-3 px-4 py-3">
          <div className="min-w-0 space-y-1">
            <div className="flex items-center gap-2">
              <span className="text-sm font-semibold text-slate-800">{s.recruitment_company}</span>
              <StatusBadge status={s.status} />
              {s.source_job_id && <span className="ltr text-xs text-slate-400">#{s.source_job_id}</span>}
            </div>
            {s.external_title && <p className="text-sm text-slate-600" dir="auto">{s.external_title}</p>}
            <p className="text-xs text-slate-500">
              {he.job.firstSeen} {formatDateTime(s.first_seen_at)} · {he.job.lastSeen} {formatDateTime(s.last_seen_at)}
            </p>
          </div>
          <a href={s.source_url} target="_blank" rel="noopener noreferrer"
             className="shrink-0 rounded-md bg-slate-900 px-3 py-1.5 text-sm font-medium text-white hover:bg-slate-700">
            {he.job.openOriginal}
          </a>
        </li>
      ))}
    </ul>
  );
}
