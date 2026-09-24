import type { JobDetail } from "../types/api";
import { he, reasonLabel, ruleLabel } from "../i18n/he";
import { EligibilityBadge, JuniorBadge, ManualBadges, RoleBadge, StatusBadge, TenderBadge } from "./StatusBadge";
import { ScoreBadge } from "./ScoreBadge";

/** Header facts for a job, plus the backend's evaluation explanation. */
export function JobCard({ job }: { job: JobDetail }) {
  const ev = job.evaluation;
  const facts: [string, React.ReactNode][] = [
    [he.job.client, job.client_company ?? he.common.none],
    [he.job.location, [job.location, job.region].filter(Boolean).join(", ") || he.common.none],
    [he.job.employmentType, job.employment_type ?? he.common.none],
    [he.job.status, <StatusBadge status={job.status} />],
    [he.job.score, <ScoreBadge score={ev?.junior_score} eligible={ev?.is_eligible} />],
    [he.job.eligibility, <EligibilityBadge eligible={ev?.is_eligible} />],
  ];
  if (job.government_ministry) facts.unshift([he.recruiter.ministry, job.government_ministry]);
  if (job.tender_number) facts.unshift([he.recruiter.tenderNumber, <span className="ltr">{job.tender_number}</span>]);
  return (
    <div className="space-y-4">
      {ev && (
        <div className="flex flex-wrap gap-1.5">
          <ManualBadges manual={job.is_manual} />
          {ev.is_government_tender && <TenderBadge />}
          {ev.is_junior && <JuniorBadge />}
          <RoleBadge role={ev.role_type} />
        </div>
      )}
      <dl className="grid grid-cols-2 gap-x-6 gap-y-3 sm:grid-cols-3">
        {facts.map(([label, value]) => (
          <div key={label}>
            <dt className="text-xs text-slate-500">{label}</dt>
            <dd className="mt-0.5 text-sm font-medium text-slate-800" dir="auto">{value}</dd>
          </div>
        ))}
      </dl>
      {ev && (ev.matched_rules.length > 0 || ev.rejection_reasons.length > 0) && (
        <div className="flex flex-wrap gap-1.5 border-t border-slate-100 pt-3">
          {ev.matched_rules.map((r) => (
            <span key={r} className="rounded bg-emerald-50 px-1.5 py-0.5 text-xs text-emerald-800">✓ {ruleLabel(r)}</span>
          ))}
          {ev.rejection_reasons.map((r) => (
            <span key={r} className="rounded bg-rose-50 px-1.5 py-0.5 text-xs text-rose-800">✗ {reasonLabel(r)}</span>
          ))}
        </div>
      )}
    </div>
  );
}
