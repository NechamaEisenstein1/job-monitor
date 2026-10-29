import { Building2, MapPin } from "lucide-react";

import type { Applications } from "../../hooks/useApplications";
import { he } from "../../i18n/he";
import { formatRelative } from "../../services/format";
import type { JobListItem } from "../../types/api";
import { Icon, LevelBadge, ManualBadges, TenderBadge } from "../StatusBadge";
import { AppliedButton } from "./AppliedButton";
import { publishedBy } from "./jobText";

/** One job in the list: only what decides "is this for me?". Everything else is in the preview. */
export function JobListCard({ job, selected, onSelect, applications }: {
  job: JobListItem;
  selected: boolean;
  onSelect: () => void;
  applications: Applications;
}) {
  return (
    <li className={`flex items-start gap-4 rounded-2xl border bg-white p-4 transition-shadow ${
      selected ? "border-brand-600 ring-3 ring-brand-50" : "border-slate-200 hover:border-slate-300"}`}>
      <div className="min-w-0 flex-1">
        <div className="mb-1.5 flex flex-wrap gap-1.5">
          <LevelBadge level={job.level} />
          {job.is_government_tender && <TenderBadge />}
          <ManualBadges featured={job.is_featured} />
        </div>
        <h2 className="text-[17px] leading-snug font-semibold">
          <button type="button" onClick={onSelect} aria-current={selected || undefined} dir="auto"
                  className="text-start text-slate-900 hover:text-brand-700 hover:underline">
            {job.title}
          </button>
        </h2>
        <div className="mt-1.5 flex flex-wrap gap-x-4 gap-y-1 text-sm text-slate-600">
          {job.client_company && (
            <span className="inline-flex items-center gap-1.5" dir="auto"><Icon icon={Building2} className="size-4 text-slate-400" />{job.client_company}</span>
          )}
          {job.location && (
            <span className="inline-flex items-center gap-1.5" dir="auto"><Icon icon={MapPin} className="size-4 text-slate-400" />{job.location}</span>
          )}
          <span>{he.job.via(publishedBy(job))}</span>
        </div>
      </div>
      <div className="flex shrink-0 flex-col items-end gap-2.5">
        <span className="text-[13px] whitespace-nowrap text-slate-500">{formatRelative(job.first_seen_at)}</span>
        <AppliedButton jobId={job.id} applications={applications} />
      </div>
    </li>
  );
}
