import { AlertTriangle, Award, Ghost, Landmark, Sparkles, Sprout, Star, TrendingUp, type LucideIcon } from "lucide-react";

import type { ChangeType, JobSignals, JobStatus, RunStatus, ScrapeStatus } from "../types/api";
import { he } from "../i18n/he";

/** Small inline icon for badges and buttons. */
export function Icon({ icon: I, className = "size-3.5" }: { icon: LucideIcon; className?: string }) {
  return <I aria-hidden className={`shrink-0 ${className}`} strokeWidth={2} />;
}

type Tone = "green" | "amber" | "red" | "slate" | "blue" | "violet";

const TONES: Record<Tone, string> = {
  green: "bg-emerald-50 text-emerald-700 ring-emerald-600/20",
  amber: "bg-amber-50 text-amber-800 ring-amber-600/20",
  red: "bg-rose-50 text-rose-700 ring-rose-600/20",
  slate: "bg-slate-100 text-slate-600 ring-slate-500/20",
  blue: "bg-sky-50 text-sky-700 ring-sky-600/20",
  violet: "bg-violet-50 text-violet-700 ring-violet-600/20",
};

// Maps backend status values to a color. Display only.
const STATUS_TONE: Record<JobStatus | RunStatus | ScrapeStatus | ChangeType, Tone> = {
  active: "green",
  not_seen_recently: "amber",
  archived: "slate",
  success: "green",
  partial: "amber",
  failed: "red",
  timeout: "red",
  network_error: "red",
  parse_error: "red",
  config_error: "red",
  zero_results: "amber",
  new: "blue",
  content_updated: "violet",
  new_source: "green",
  source_url_updated: "slate",
};

export function Badge({ tone, children }: { tone: Tone; children: React.ReactNode }) {
  return (
    <span className={`inline-flex items-center gap-1 whitespace-nowrap rounded-md px-2 py-0.5 text-xs font-medium ring-1 ring-inset ${TONES[tone]}`}>
      {children}
    </span>
  );
}

export function StatusBadge({ status }: { status: keyof typeof STATUS_TONE | null | undefined }) {
  if (!status) return <Badge tone="slate">{he.sources.neverRun}</Badge>;
  return <Badge tone={STATUS_TONE[status] ?? "slate"}>{he.status[status] ?? status}</Badge>;
}

export function EligibilityBadge({ eligible }: { eligible: boolean | null | undefined }) {
  if (eligible == null) return <Badge tone="slate">{he.eligibility.notEvaluated}</Badge>;
  return eligible
    ? <Badge tone="green">{he.eligibility.eligible}</Badge>
    : <Badge tone="slate">{he.eligibility.notEligible}</Badge>;
}

/** Government tender: the one badge meant to catch the eye (filled, with an icon). */
export function TenderBadge() {
  return (
    <span className="inline-flex items-center gap-1 whitespace-nowrap rounded-md bg-amber-400 px-2 py-0.5 text-xs font-semibold text-amber-950">
      <Icon icon={Landmark} />{he.tender}
    </span>
  );
}

/** Honesty labels: new / likely a standing ad / several agencies / misleading "junior". */
export function SignalBadges({ signals, fakeJunior, years }: {
  signals: JobSignals | null | undefined; fakeJunior?: boolean; years?: number | null;
}) {
  const t = he.signals;
  return (
    <>
      {fakeJunior && <span title={t.fakeJuniorHint}><Badge tone="red"><Icon icon={AlertTriangle} />{t.fakeJunior(years ?? null)}</Badge></span>}
      {signals?.is_new && <span title={t.newHint}><Badge tone="green"><Icon icon={Sparkles} />{t.isNew}</Badge></span>}
      {signals?.is_ghost && (
        <span title={t.ghostHint(signals.days_open, signals.reposts)}><Badge tone="amber"><Icon icon={Ghost} />{t.ghost}</Badge></span>
      )}
      {signals && signals.agency_count > 1 && (
        <span title={t.agenciesHint(signals.first_agency)}><Badge tone="blue">{t.agencies(signals.agency_count)}</Badge></span>
      )}
    </>
  );
}

/** A posting a recruiter published on this site (not scraped), and its paid placement. */
export function ManualBadges({ manual, featured }: { manual?: boolean; featured?: boolean }) {
  return (
    <>
      {featured && <Badge tone="violet"><Icon icon={Star} />{he.featured}</Badge>}
      {manual && <Badge tone="blue">{he.manual}</Badge>}
    </>
  );
}

export function RoleBadge({ role }: { role: string | null | undefined }) {
  if (!role) return null;
  return <Badge tone={role === "software" ? "blue" : "slate"}>{he.roles[role] ?? role}</Badge>;
}

/** Experience level, on every job: filled and bright so the mix of levels shows at a glance. */
const LEVELS: Record<string, { icon: LucideIcon; className: string }> = {
  a: { icon: Sprout, className: "bg-emerald-500 text-white" },
  b: { icon: TrendingUp, className: "bg-sky-600 text-white" },
  c: { icon: Award, className: "bg-violet-600 text-white" },
};

export function LevelBadge({ level }: { level: string | null | undefined }) {
  const style = level ? LEVELS[level] : undefined;
  if (!level || !style) return null;
  return (
    <span title={he.myArea.levels[level]}
          className={`inline-flex items-center gap-1 whitespace-nowrap rounded-md px-2 py-0.5 text-xs font-semibold ${style.className}`}>
      <Icon icon={style.icon} />{he.levelBadge[level]}
    </span>
  );
}
