import { Link } from "react-router-dom";

import type { JobChange } from "../types/api";
import { he } from "../i18n/he";
import { formatDateTime } from "../services/format";
import { StatusBadge } from "./StatusBadge";

export function ChangeList({ changes, showJob = true }: { changes: JobChange[]; showJob?: boolean }) {
  return (
    <ul className="divide-y divide-slate-100">
      {changes.map((c) => (
        <li key={c.id} className="flex flex-wrap items-center gap-x-3 gap-y-1 px-4 py-2.5 text-sm">
          <StatusBadge status={c.change_type} />
          {showJob && (
            <Link to={`/jobs/${c.job_id}`} className="min-w-0 flex-1 truncate font-medium text-slate-800 hover:underline" dir="auto">
              {c.job_title}
            </Link>
          )}
          <span className={`text-xs text-slate-500 ${showJob ? "" : "flex-1"}`}>{he.job.via(c.recruitment_company)}</span>
          <span className="whitespace-nowrap text-xs tabular-nums text-slate-500">{formatDateTime(c.created_at)}</span>
        </li>
      ))}
    </ul>
  );
}
