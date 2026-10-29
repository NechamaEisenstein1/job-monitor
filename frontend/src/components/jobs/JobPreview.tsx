import { ChevronLeft, ChevronRight, ExternalLink, Maximize2 } from "lucide-react";
import { Link } from "react-router-dom";

import type { Applications } from "../../hooks/useApplications";
import { useApi } from "../../hooks/useApi";
import type { Verifications } from "../../hooks/useVerifications";
import { he } from "../../i18n/he";
import { api } from "../../services/api";
import { formatRelative } from "../../services/format";
import type { JobListItem } from "../../types/api";
import { ErrorState, LoadingState } from "../States";
import { Icon, LevelBadge, ManualBadges, RoleBadge, SignalBadges, TenderBadge } from "../StatusBadge";
import { button, iconButton } from "../ui/button";
import { ReliabilityBadge, VerifyButton } from "../VerifyButton";
import { AppliedButton } from "./AppliedButton";
import { publishedBy } from "./jobText";
import { TextBlock } from "./TextBlock";

export interface PreviewNavigation {
  /** "Job 3 of 312". */
  position: string;
  onPrevious: (() => void) | undefined;
  onNext: (() => void) | undefined;
}

/** The selected job in full: facts, labels, description and actions. The list item fills the
 *  header at once; description and sources load in the background. */
export function JobPreview({ job, navigation, applications, verifications }: {
  job: JobListItem;
  navigation: PreviewNavigation;
  applications: Applications;
  verifications: Verifications;
}) {
  const detail = useApi(() => api.job(job.id), `job-${job.id}`);
  const sources = useApi(() => (job.is_manual ? Promise.resolve([]) : api.jobSources(job.id)), `sources-${job.id}`);
  const original = sources.data?.find((s) => s.status === "active") ?? sources.data?.[0];
  const d = detail.data;

  const facts: [string, React.ReactNode][] = [
    [he.job.client, job.client_company],
    [he.job.location, job.location],
    [he.job.publishedBy, publishedBy(job)],
    [he.job.posted, formatRelative(job.first_seen_at)],
    [he.job.employmentType, d?.employment_type],
    [he.recruiter.ministry, job.government_ministry],
    [he.recruiter.tenderNumber, job.tender_number && <span className="ltr">{job.tender_number}</span>],
  ];

  return (
    <article className="flex h-full flex-col">
      <header className="border-b border-slate-100 px-5 pt-4 pb-5">
        <div className="mb-3 flex items-center justify-between gap-3">
          <span className="text-[13px] text-slate-500">{navigation.position}</span>
          <div className="flex gap-1 pe-10 lg:pe-0">
            <button type="button" className={iconButton("sm")} aria-label={he.jobs.previous}
                    disabled={!navigation.onPrevious} onClick={navigation.onPrevious}>
              <Icon icon={ChevronRight} className="size-4" />
            </button>
            <button type="button" className={iconButton("sm")} aria-label={he.jobs.next}
                    disabled={!navigation.onNext} onClick={navigation.onNext}>
              <Icon icon={ChevronLeft} className="size-4" />
            </button>
          </div>
        </div>
        <div className="mb-2 flex flex-wrap gap-1.5">
          <LevelBadge level={job.level} />
          {job.is_government_tender && <TenderBadge />}
          <ManualBadges manual={job.is_manual} featured={job.is_featured} />
        </div>
        <h2 className="text-[22px] leading-tight font-bold tracking-tight" dir="auto">{job.title}</h2>
        <dl className="mt-4 grid grid-cols-2 gap-x-5 gap-y-3">
          {facts.filter(([, value]) => value).map(([label, value]) => (
            <div key={label} className="min-w-0">
              <dt className="text-[12.5px] text-slate-500">{label}</dt>
              <dd className="mt-0.5 text-[14.5px] font-medium" dir="auto">{value}</dd>
            </div>
          ))}
        </dl>
        <div className="mt-3.5 flex flex-wrap gap-1.5">
          <ReliabilityBadge reliability={verifications.latest[job.id]?.reliability ?? job.reliability} />
          <RoleBadge role={job.role_type} />
          <SignalBadges signals={job.signals} fakeJunior={job.junior_title_mismatch} years={job.required_years} />
        </div>
      </header>

      <div className="min-h-0 flex-1 space-y-4 overflow-y-auto px-5 py-4">
        {detail.error ? <ErrorState error={detail.error} onRetry={detail.reload} />
          : !d ? <LoadingState rows={5} />
          : (
            <>
              <section>
                <h3 className="mb-1.5 font-semibold">{he.job.description}</h3>
                <TextBlock text={d.description} />
              </section>
              <section>
                <h3 className="mb-1.5 font-semibold">{he.job.requirements}</h3>
                <TextBlock text={d.requirements} />
              </section>
            </>
          )}
      </div>

      <footer className="flex flex-wrap items-center gap-2 border-t border-slate-100 px-5 py-4">
        {original && (
          <a href={original.source_url} target="_blank" rel="noopener noreferrer" className={`${button("primary", "md")} flex-[1_1_12rem]`}>
            {he.job.openOriginalShort}<Icon icon={ExternalLink} className="size-4" />
          </a>
        )}
        <AppliedButton jobId={job.id} applications={applications} size="md" />
        <VerifyButton job={job} verifications={verifications} />
        <Link to={`/jobs/${job.id}`} className={button("ghost", "md")}>
          <Icon icon={Maximize2} className="size-4" />{he.job.fullPage}
        </Link>
      </footer>
    </article>
  );
}
