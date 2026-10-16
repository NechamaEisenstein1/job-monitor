import { Link } from "react-router-dom";

import type { Applications } from "../hooks/useApplications";
import type { JobListItem } from "../types/api";
import { AppliedCheckbox } from "./AppliedCheckbox";
import { he } from "../i18n/he";
import { formatDate, formatRelative } from "../services/format";
import { MapPin } from "lucide-react";

import { Icon, LevelBadge, ManualBadges, RoleBadge, SignalBadges, StatusBadge, TenderBadge } from "./StatusBadge";
import { td, th } from "./Layout";

const c = he.jobs.columns;

export function JobTable({ jobs, applications }: { jobs: JobListItem[]; applications?: Applications }) {
  return (
    <div className="overflow-x-auto">
      <table className="min-w-full divide-y divide-slate-100">
        <thead className="bg-slate-50">
          <tr>
            {[c.title, c.client, c.location, c.status, c.sources, c.lastSeen, c.updated].map((h) => (
              <th key={h} className={th}>{h}</th>
            ))}
            {applications && <th className={th}>{he.applied.column}</th>}
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-100">
          {jobs.map((job) => (
            <tr key={job.id} className={job.is_government_tender ? "bg-amber-50/40 hover:bg-amber-50" : "hover:bg-slate-50"}>
              <td className={`${td} max-w-xs`}>
                <Link to={`/jobs/${job.id}`} target="_blank" rel="noopener"
                      className="font-medium text-slate-900 hover:text-sky-700 hover:underline" dir="auto">
                  {job.title}
                </Link>
                <div className="mt-1 flex flex-wrap gap-1">
                  <LevelBadge level={job.level} />
                  <SignalBadges signals={job.signals} fakeJunior={job.junior_title_mismatch} years={job.required_years} />
                  <ManualBadges manual={job.is_manual} featured={job.is_featured} />
                  {job.is_government_tender && <TenderBadge />}
                  <RoleBadge role={job.role_type} />
                </div>
              </td>
              <td className={td} dir="auto">
                {job.client_company ?? he.common.none}
                {job.tender_number && <div className="text-xs text-slate-500">{he.recruiter.tenderNumber}: <span className="ltr">{job.tender_number}</span></div>}
              </td>
              <td className={td} dir="auto">
                {job.location
                  ? <span className="inline-flex items-center gap-1"><Icon icon={MapPin} className="size-3.5 text-slate-400" />{job.location}</span>
                  : he.common.none}
              </td>
              <td className={td}><StatusBadge status={job.status} /></td>
              <td className={td} title={job.recruitment_companies.join(", ")}>
                <span className="inline-flex items-baseline gap-1.5 whitespace-nowrap">
                  <span className="tabular-nums">{job.source_count}</span>
                  <span className="text-xs text-slate-400">{job.is_manual ? he.manual : job.recruitment_companies.join(", ")}</span>
                </span>
              </td>
              <td className={`${td} whitespace-nowrap`}>{formatRelative(job.last_seen_at)}</td>
              <td className={`${td} whitespace-nowrap`}>{formatDate(job.updated_at)}</td>
              {applications && <td className={td}><AppliedCheckbox jobId={job.id} applications={applications} /></td>}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
