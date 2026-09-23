import { Link } from "react-router-dom";

import type { JobListItem } from "../types/api";
import { he } from "../i18n/he";
import { formatDate, formatRelative } from "../services/format";
import { ScoreBadge } from "./ScoreBadge";
import { JuniorBadge, RoleBadge, StatusBadge, TenderBadge } from "./StatusBadge";
import { td, th } from "./Layout";

const c = he.jobs.columns;

export function JobTable({ jobs }: { jobs: JobListItem[] }) {
  return (
    <div className="overflow-x-auto">
      <table className="min-w-full divide-y divide-slate-100">
        <thead className="bg-slate-50">
          <tr>
            {[c.title, c.client, c.location, c.score, c.status, c.sources, c.lastSeen, c.updated].map((h) => (
              <th key={h} className={th}>{h}</th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-100">
          {jobs.map((job) => (
            <tr key={job.id} className="hover:bg-slate-50">
              <td className={`${td} max-w-xs`}>
                <Link to={`/jobs/${job.id}`} className="font-medium text-slate-900 hover:text-sky-700 hover:underline" dir="auto">
                  {job.title}
                </Link>
                <div className="mt-1 flex flex-wrap gap-1">
                  {job.is_government_tender && <TenderBadge />}
                  {job.is_junior && <JuniorBadge />}
                  <RoleBadge role={job.role_type} />
                </div>
              </td>
              <td className={td} dir="auto">{job.client_company ?? he.common.none}</td>
              <td className={td} dir="auto">{job.location ?? he.common.none}</td>
              <td className={td}><ScoreBadge score={job.junior_score} eligible={job.is_eligible} /></td>
              <td className={td}><StatusBadge status={job.status} /></td>
              <td className={td} title={job.recruitment_companies.join(", ")}>
                <span className="inline-flex items-baseline gap-1.5 whitespace-nowrap">
                  <span className="tabular-nums">{job.source_count}</span>
                  <span className="text-xs text-slate-400">{job.recruitment_companies.join(", ")}</span>
                </span>
              </td>
              <td className={`${td} whitespace-nowrap`}>{formatRelative(job.last_seen_at)}</td>
              <td className={`${td} whitespace-nowrap`}>{formatDate(job.updated_at)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
